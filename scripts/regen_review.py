#!/usr/bin/env python3
"""
Regenerate paper-faithful code-review samples (v1 #91-#100) from
`data/v1_review_criteria.json`.

This is the atomic_skills paper definition (Ma et al. arXiv:2604.05013
Appendix E): the agent receives a PR description + PR code in plan mode,
explores the repo read-only, and emits a structured judgment.

Schema (per sample)
-------------------
    {
      "id": 91,
      "name": "pr_review_iter_slices_yes",
      "source_manifest": "data/v1_editing_criteria.json",
      "source_id": 51,
      "variant": "reference_edit" | "mutants[N]",
      "label": "YES" | "NO",
      "issue_text": "<bug-tracker-voice description>",
      "structural_signature": {...}    # optional metadata
    }

Cross-reference rules
---------------------
- The (`source_manifest`, `source_id`, `variant`) triple resolves to a
  patch (`oldString`/`newString` pair) on a specific path inside the
  pinned `requests` checkout.
- `variant == "reference_edit"`: use `source.reference_edit` (single-file
  form) or each `source.targets[i].reference_edit` (multi-file form).
- `variant == "mutants[N]"`: use `source.mutants[N].patch` and
  `source.mutants[N].path` (defaults to single-file `source.file` or
  `source.targets[0].path`).
- `label` MUST match the truth-table outcome under that variant: YES iff
  exec_assert PASSES, NO iff at least one assert FAILS. This is enforced
  mechanically by `scripts/audit_review.py`.

Prompt construction
-------------------
The prompt embeds the issue text plus a unified-diff-formatted patch
generated at regen time from the variant's oldString/newString. The
agent is told to read the repo to verify the judgment. Plan mode is
implied by `agent: "plan"` in the row.

Pass criteria
-------------
1. `no_tool_name [edit, bash, write]` — plan-mode adherence
2. `text_contains <judgment>{LABEL}</judgment>` — gold-gated
3. `text_contains <review>` AND `</review>` — structured-output discipline
4. `call_schema_valid` — tool hygiene

Usage
-----
    python3 scripts/regen_review.py            # regenerate everything
    python3 scripts/regen_review.py --dry-run  # plan only, no writes
    python3 scripts/regen_review.py --id 91    # one sample
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import PROJECTS  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "v1_review_criteria.json"
V1_REQUESTS_ROOT = PROJECTS / "v1" / "requests"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"

REVIEW_IDS = set(range(91, 101))

VALID_LABELS = {"YES", "NO"}


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open() as f:
        return json.load(f)


def pin_short() -> str:
    try:
        repos = json.loads((ROOT / "data" / "v1_repos.json").read_text())
        sha = repos.get("requests", {}).get("pin") or ""
        return sha[:12] if sha else "unknown"
    except (json.JSONDecodeError, OSError):
        return "unknown"


def load_source_entry(source_manifest: str, source_id: int) -> dict[str, Any]:
    """Resolve a (source_manifest_path, source_id) pair to a manifest entry."""
    sp = ROOT / source_manifest
    sm = json.loads(sp.read_text())
    for entry in sm.get("samples", []):
        if entry.get("id") == source_id:
            return entry
    raise KeyError(f"source_id {source_id} not found in {source_manifest}")


# ---------------------------------------------------------------------------
# Variant resolution: (source_entry, variant) -> list of (path, oldString, newString)
# ---------------------------------------------------------------------------


def parse_variant(variant: str) -> tuple[str, int | None]:
    """Return (kind, index) where kind is 'reference_edit' or 'mutants'."""
    variant = variant.strip()
    if variant == "reference_edit":
        return ("reference_edit", None)
    if variant.startswith("mutants[") and variant.endswith("]"):
        try:
            idx = int(variant[len("mutants["):-1])
        except ValueError as e:
            raise ValueError(f"unparseable variant {variant!r}: {e}")
        return ("mutants", idx)
    raise ValueError(
        f"unknown variant {variant!r}; expected 'reference_edit' or 'mutants[N]'"
    )


def resolve_patches(source: dict, variant: str) -> list[dict]:
    """Return list of {path, oldString, newString} patches for the variant.

    YES variants -> derived from source's reference_edit (one patch per target).
    NO variants  -> derived from source.mutants[idx]; mutant declares its own
                    `path` (default: source's primary path).
    """
    kind, idx = parse_variant(variant)
    if kind == "reference_edit":
        if source.get("targets"):
            return [
                {
                    "path": t["path"],
                    "oldString": t["reference_edit"]["oldString"],
                    "newString": t["reference_edit"]["newString"],
                }
                for t in source["targets"]
            ]
        return [
            {
                "path": source["file"],
                "oldString": source["reference_edit"]["oldString"],
                "newString": source["reference_edit"]["newString"],
            }
        ]
    # mutants[N]
    mutants = source.get("mutants") or []
    if idx >= len(mutants):
        raise IndexError(
            f"source #{source['id']}: mutants[{idx}] out of range "
            f"(have {len(mutants)})"
        )
    mut = mutants[idx]
    patch = mut.get("patch")
    if not patch:
        raise ValueError(
            f"source #{source['id']}: mutants[{idx}] has null/missing patch"
        )
    default_path = (
        source.get("targets", [{}])[0].get("path") if source.get("targets") else source.get("file")
    )
    path = mut.get("path") or default_path
    return [
        {
            "path": path,
            "oldString": patch["oldString"],
            "newString": patch["newString"],
        }
    ]


def render_unified_diff(patches: list[dict]) -> str:
    """Render a list of {path, oldString, newString} as a single unified diff."""
    chunks: list[str] = []
    for p in patches:
        path = p["path"]
        old_lines = p["oldString"].splitlines(keepends=True)
        new_lines = p["newString"].splitlines(keepends=True)
        # Make sure each "side" ends with a newline so difflib produces clean hunks.
        if old_lines and not old_lines[-1].endswith("\n"):
            old_lines[-1] += "\n"
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                n=3,
            )
        )
        chunks.append("".join(diff_lines))
    return "".join(chunks).rstrip("\n")


# ---------------------------------------------------------------------------
# Prompt construction (paper Appendix E)
# ---------------------------------------------------------------------------


PROMPT_TEMPLATE = """\
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
{issue_text}
</pr_description>

<pr_code>
{unified_diff}
</pr_code>

Review the pr_code to determine whether it correctly fixes the issue described above. After your review, provide:

<review>
Your detailed review. Cite specific lines or functions where relevant.
</review>

<judgment>
YES or NO
</judgment>

Use "YES" if the pr_code correctly fixes the issue. Use "NO" if it does not."""


def build_prompt(entry: dict, source: dict) -> str:
    issue = (entry.get("issue_text") or "").strip()
    if not issue:
        raise ValueError(f"#{entry['id']}: issue_text is required")
    patches = resolve_patches(source, entry["variant"])
    diff = render_unified_diff(patches)
    if not diff:
        raise ValueError(
            f"#{entry['id']}: rendered diff is empty (variant={entry['variant']!r})"
        )
    return PROMPT_TEMPLATE.format(issue_text=issue, unified_diff=diff)


# ---------------------------------------------------------------------------
# Row + spec rendering
# ---------------------------------------------------------------------------


def _checks_for_row(entry: dict) -> list[dict]:
    """4 checks: no_tool_name, text_contains <judgment>LABEL</judgment>,
    text_contains <review> + </review>, call_schema_valid."""
    label = entry["label"]
    return [
        {
            "type": "no_tool_name",
            "not_equals": ["edit", "bash", "write"],
            "description": "plan mode: no mutations or shell execution",
        },
        {
            "type": "text_contains",
            "pattern": rf"<judgment>\s*{label}\s*</judgment>",
            "description": f"final judgment block contains exactly {label}",
        },
        {
            "type": "text_contains",
            "pattern": r"<review>[\s\S]*?</review>",
            "description": "response includes a non-empty <review>...</review> block",
        },
        {
            "type": "call_schema_valid",
            "description": "all tool calls match opencode schemas",
        },
    ]


def build_row(entry: dict, prompt: str) -> dict:
    sid = entry["id"]
    row: dict[str, Any] = {
        "id": sid,
        "version": "v1",
        "repo": "requests",
        "name": entry["name"],
        "category": "code_review",
        "contract": "routing",
        "surface": "modes",
        "agent": "plan",
        "min_calls": entry.get("min_calls", 0),
        "difficulty": entry.get("difficulty", "medium"),
        "prompt": prompt,
        "checks": _checks_for_row(entry),
    }
    sig = entry.get("structural_signature")
    if sig:
        row["structural_signature"] = dict(sig)
    return row


SPEC_TEMPLATE = """\
# v1 #{sid} {name}

## Category

code_review

## Contract

routing

## Surface

modes (`--agent plan`)

## Paper reference

Ma et al., arXiv:2604.05013, Appendix E. The agent acts as a code reviewer:
given a PR description + PR diff, it explores the repo read-only and emits a
structured `<judgment>YES|NO</judgment>` plus a `<review>` summary.

## Source cross-reference

This sample reuses material from the `code_editing` source manifest (no new bugs authored):

- source_manifest: `{source_manifest}`
- source_id: **#{source_id}** ({source_name})
- variant: **{variant}**
- gold label: **{label}**

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> {issue_blockquote}

## PR under review (in prompt as `<pr_code>`)

Unified diff constructed from the source manifest's `{variant}` for source #{source_id}, against pin `{pin_short}`:

```diff
{diff_block}
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
{prompt_codeblock}
```

## Pass criteria (4 checks)

1. `no_tool_name` not in `[edit, bash, write]` — plan-mode adherence (the agent must not modify files or execute code)
2. `text_contains` `<judgment>\\s*{label}\\s*</judgment>` — gold-gated structured judgment
3. `text_contains` `<review>[\\s\\S]*?</review>` — non-empty `<review>` block (structured-output discipline)
4. `call_schema_valid` — every read/grep/glob call matches opencode's canonical JSON schemas

## Label oracle (graders only)

Mechanical proof that label = `{label}` is correct: apply the {variant} patch from source #{source_id} on top of the pinned baseline, then run `exec_assert` against the source's truth table. The label must match the outcome:

- `label=YES` -> exec_assert PASSES (all asserts in source.asserts evaluate True)
- `label=NO` -> exec_assert FAILS at least one assert

Verified mechanically by `python3 scripts/audit_review.py --id {sid}` (Pass 1).

## Shortest path

**1-3 tool calls**: read the affected file(s) under `src/requests/` (typically 1 read for single-file diffs, 2 for multi-file), then synthesize the judgment in the response. The diff is already in the prompt; the agent's job is to verify it actually addresses the issue.

## Fail modes

- Uses `edit` / `write` / `bash` -- violates plan-mode (check 1).
- Outputs the wrong judgment for the gold label (check 2).
- Forgets the `<review>` block (check 3).
- Malformed read-tool args (check 4).
- Confidently judges YES/NO without reading the actual source -- not directly checked, but the issue text deliberately omits enough detail that a no-read judgment is unreliable.

## Intentionally *not* checked

- Free-form text in `<review>` -- the review summary is required by the prompt (per the paper) but its content is not graded.
- Whether the agent uses `read`, `grep`, or `glob` -- any read-only tool mix is acceptable.
- Number of tool calls -- plan mode samples have `min_calls: 0` (a confident reader can skip exploration).

## Note on methodology

This sample is the paper-faithful `code_review` atomic skill (Ma et al. arXiv:2604.05013), implemented via cross-reference to the `code_editing` source manifest. The PR diff is constructed mechanically; the gold label is mechanically derived from `exec_assert` against the source's truth table. The agent's role is to JUDGE, not to PATCH.

If the source manifest changes, re-run `scripts/regen_review.py` and `scripts/audit_review.py`.

## Lock-in hash

SHA-256 of `(source_manifest, source_id, variant, label, issue_text)` JSON-serialized with sorted keys. Drift in any of these fields changes the hash. Cross-referenced in [data/v1_review_lock_in.md](../../v1_review_lock_in.md).

`{lock_in_hash}`
"""


def lock_in_hash(entry: dict) -> str:
    payload = {
        "source_manifest": entry.get("source_manifest", ""),
        "source_id": entry.get("source_id"),
        "variant": entry.get("variant", ""),
        "label": entry.get("label", ""),
        "issue_text": entry.get("issue_text", ""),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def render_spec(entry: dict, source: dict, prompt: str, pin: str) -> str:
    issue_quote = (entry.get("issue_text") or "").rstrip().replace("\n", "\n> ")
    diff = render_unified_diff(resolve_patches(source, entry["variant"]))
    return SPEC_TEMPLATE.format(
        sid=entry["id"],
        name=entry["name"],
        source_manifest=entry["source_manifest"],
        source_id=entry["source_id"],
        source_name=source["name"],
        variant=entry["variant"],
        label=entry["label"],
        issue_blockquote=issue_quote,
        pin_short=pin,
        diff_block=diff,
        prompt_codeblock=prompt.rstrip(),
        lock_in_hash=lock_in_hash(entry),
    )


# ---------------------------------------------------------------------------
# Authoring gates
# ---------------------------------------------------------------------------


REQUIRED_FIELDS = ("name", "source_manifest", "source_id", "variant", "label", "issue_text")


def authoring_gates(entry: dict, source: dict) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    for fld in REQUIRED_FIELDS:
        v = entry.get(fld)
        if v is None or (isinstance(v, str) and not v.strip()):
            errors.append(f"{prefix}: required field {fld!r} missing or empty")
    if not (51 <= entry.get("source_id", 0) <= 60):
        errors.append(
            f"{prefix}: source_id {entry.get('source_id')} not in [51, 60]; "
            f"the plan only authorizes #51-#60 as sources"
        )
    label = entry.get("label")
    if label not in VALID_LABELS:
        errors.append(f"{prefix}: label {label!r} not in {sorted(VALID_LABELS)}")

    # Variant resolution must succeed.
    try:
        patches = resolve_patches(source, entry["variant"])
    except (KeyError, IndexError, ValueError) as e:
        errors.append(f"{prefix}: variant resolution failed: {e}")
        return errors

    # Each patch's oldString must occur exactly once in its target file at the pin.
    for i, p in enumerate(patches):
        path = V1_REQUESTS_ROOT / p["path"]
        try:
            src_text = path.read_text()
        except FileNotFoundError as e:
            errors.append(f"{prefix}: patch[{i}] target {p['path']!r} not found: {e}")
            continue
        n = src_text.count(p["oldString"])
        if n != 1:
            errors.append(
                f"{prefix}: patch[{i}] {p['path']}: oldString occurs {n} times "
                f"(expected exactly 1) at pin"
            )

    # issue_text must NOT verbatim-leak the new code from the diff (would give
    # away the answer to the agent before they read anything).
    issue = entry.get("issue_text") or ""
    for i, p in enumerate(patches):
        new_lines = [
            ln.strip()
            for ln in p["newString"].splitlines()
            if ln.strip() and len(ln.strip()) >= 20
        ]
        for ln in new_lines:
            if ln in issue:
                errors.append(
                    f"{prefix}: issue_text appears to leak verbatim a line from the diff: {ln!r}"
                )
                break

    return errors


# ---------------------------------------------------------------------------
# File rewrite helpers
# ---------------------------------------------------------------------------


def rewrite_specs(entries: list[tuple[dict, dict, str]], pin: str, dry_run: bool) -> None:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    keep_paths: set[Path] = set()
    for entry, source, prompt in entries:
        sid = entry["id"]
        spec_path = SPEC_DIR / f"{sid:03d}_{entry['name']}.md"
        content = render_spec(entry, source, prompt, pin)
        keep_paths.add(spec_path)
        if dry_run:
            print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(content)} bytes)")
        else:
            spec_path.write_text(content)
            print(f"  wrote {spec_path.relative_to(ROOT)} ({len(content)} bytes)")

    # Prune stale review-id specs whose name no longer matches manifest.
    ids_in_manifest = {e["id"] for e, _, _ in entries}
    stale_globs = list(SPEC_DIR.glob("09[0-9]_*.md")) + list(SPEC_DIR.glob("100_*.md"))
    for stale in sorted(stale_globs):
        try:
            stale_id = int(stale.name[:3])
        except ValueError:
            continue
        if stale_id not in REVIEW_IDS:
            continue
        if stale_id not in ids_in_manifest:
            continue
        if stale in keep_paths:
            continue
        if dry_run:
            print(f"  [dry-run] would delete stale spec {stale.relative_to(ROOT)}")
        else:
            stale.unlink()
            print(f"  deleted stale spec {stale.relative_to(ROOT)}")


def rewrite_jsonl(entries: list[tuple[dict, dict, str]], dry_run: bool) -> None:
    new_rows_by_id: dict[int, dict] = {
        entry["id"]: build_row(entry, prompt) for entry, _, prompt in entries
    }
    review_ids = set(new_rows_by_id)
    out_lines: list[str] = []
    seen_ids: set[int] = set()
    existing: list[str] = []
    if SAMPLES_JSONL.exists():
        existing = SAMPLES_JSONL.read_text().splitlines()
    for raw in existing:
        line = raw.rstrip("\n")
        if not line.strip():
            out_lines.append(line)
            continue
        s = json.loads(line)
        if s.get("id") in review_ids:
            sid = s["id"]
            if sid in seen_ids:
                raise RuntimeError(f"duplicate row for id {sid} in samples_v1.jsonl")
            seen_ids.add(sid)
            out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))
        else:
            out_lines.append(line)
    for sid in sorted(review_ids - seen_ids):
        out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))
    new_content = "\n".join(out_lines) + "\n"
    if dry_run:
        print(
            f"  [dry-run] would write {SAMPLES_JSONL.relative_to(ROOT)} "
            f"({len(new_content)} bytes, {len(out_lines)} rows)"
        )
        return
    SAMPLES_JSONL.write_text(new_content)
    print(
        f"  wrote {SAMPLES_JSONL.relative_to(ROOT)} "
        f"({len(new_content)} bytes, {len(out_lines)} rows)"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--id", type=int, action="append")
    args = p.parse_args()

    manifest = load_manifest()
    samples = manifest.get("samples", [])
    if not isinstance(samples, list):
        print("ERROR: manifest 'samples' is not a list", file=sys.stderr)
        return 2
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]
        missing = wanted - {s["id"] for s in samples}
        if missing:
            print(f"ERROR: manifest missing ids {sorted(missing)}", file=sys.stderr)
            return 2
    if not samples:
        print("(empty manifest -- nothing to regenerate)")
        return 0

    print("=" * 60)
    print("Running authoring gates")
    print("=" * 60)
    entries: list[tuple[dict, dict, str]] = []
    any_error = False
    for entry in samples:
        sid = entry["id"]
        name = entry.get("name", "?")
        if sid not in REVIEW_IDS:
            print(f"  SKIP #{sid} {name} (not in review id range 91-100)")
            continue
        try:
            source = load_source_entry(entry["source_manifest"], entry["source_id"])
        except (FileNotFoundError, KeyError) as e:
            print(f"  FAIL #{sid} {name}: source resolution: {e}", file=sys.stderr)
            any_error = True
            continue
        errs = authoring_gates(entry, source)
        if errs:
            print(f"  FAIL #{sid} {name}")
            for er in errs:
                print(f"    - {er}")
            any_error = True
            continue
        try:
            prompt = build_prompt(entry, source)
        except ValueError as e:
            print(f"  FAIL #{sid} {name}: prompt build: {e}", file=sys.stderr)
            any_error = True
            continue
        print(f"  PASS #{sid} {name}")
        entries.append((entry, source, prompt))

    if any_error:
        print()
        print("RESULT: FAIL (authoring gates rejected one or more samples)")
        return 1

    print()
    print("=" * 60)
    print("Writing spec files")
    print("=" * 60)
    rewrite_specs(entries, pin_short(), args.dry_run)
    print()
    print("=" * 60)
    print("Rewriting data/samples_v1.jsonl")
    print("=" * 60)
    rewrite_jsonl(entries, args.dry_run)
    print()
    print("=" * 60)
    if args.dry_run:
        print("RESULT: DRY-RUN OK (no files written)")
    else:
        print(f"RESULT: OK ({len(entries)} samples regenerated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
