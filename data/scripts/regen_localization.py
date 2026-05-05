#!/usr/bin/env python3
"""
Regenerate criterion-anchored code-localization samples (v1 #21-#30) from
`data/v1_localization_criteria.json`.

The manifest is the single source of truth. For each sample entry it lists:

    id               - sample id (21..30)
    name             - short name, used for the spec filename + jsonl.name
    scope            - path (relative to the pinned submodule) to search
    tokens           - list of identifier strings to match as whole-word,
                       case-sensitive tokens

For each entry this script:

    1. Runs the canonical generator
           rg -l -w -e <tok1> -e <tok2> ... <scope>
       against `projects/v1/requests/` and sorts the resulting file list.
    2. Asserts |F*| >= 5 and that all entries are regular files that exist.
    3. Rewrites `data/specs/v1/<NNN>_<name>.md` using the new
       criterion-anchored spec template (see `render_spec`).
    4. Deletes any stale spec files for ids 21..30 whose filename no
       longer matches the current manifest name.
    5. Rewrites the corresponding rows in `data/samples_v1.jsonl`
       (replacing the existing rows for ids 21..30 in place, preserving
       line order relative to non-localization samples).

This script is idempotent: running it twice with the same manifest against
the same submodule pin produces byte-identical spec files and jsonl rows.

The resulting samples use the same two checks as before:

    * file_regex_disk  -- anchored regex over sorted F*
    * call_schema_valid

so no changes to the evaluators are required.

This is a deliberate departure from semantic file-level localization per
`arXiv:2604.05013`. The task now tests precise-criterion comprehension,
effective search, and exact output formatting rather than subjective
"participates in subsystem X" judgments. See the "Note on methodology"
section in each generated spec for details.

Usage
-----
    python3 data/scripts/regen_localization.py           # regenerate everything
    python3 data/scripts/regen_localization.py --dry-run # print plan, no writes
    python3 data/scripts/regen_localization.py --id 27   # just one sample
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import PROJECTS  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_localization_criteria.json"
V1_REQUESTS_ROOT = PROJECTS / "v1" / "requests"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"

MIN_FILES = 5


# ---------------------------------------------------------------------------
# Manifest loading + canonical generator
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open() as f:
        return json.load(f)


def compute_f_star(scope: str, tokens: list[str]) -> list[str]:
    """Run the canonical generator and return a sorted list of repo-relative paths.

    The canonical generator is
        rg -l -w -e <tok1> -e <tok2> ... <scope>
    invoked from `projects/v1/requests/`. rg's `-w` gives whole-word matches;
    case-sensitivity is rg's default. The returned paths are always
    repo-relative (that is, relative to the workspace root seen by the agent,
    which is the submodule checkout), normalized to forward slashes, and
    sorted with Python's default string ordering.
    """
    cmd = ["rg", "-l", "-w"]
    for tok in tokens:
        cmd += ["-e", tok]
    cmd.append(scope)
    proc = subprocess.run(
        cmd,
        cwd=str(V1_REQUESTS_ROOT),
        capture_output=True,
        text=True,
    )
    # rg exits 1 when there are zero matches -- that's a manifest bug for us.
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"rg failed (rc={proc.returncode}) for scope={scope!r} tokens={tokens!r}\n"
            f"stderr: {proc.stderr.strip()}"
        )
    paths = sorted(
        line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()
    )
    return paths


def canonical_generator_cmd(scope: str, tokens: list[str]) -> str:
    """Human-readable generator command for docs/specs."""
    parts = ["rg", "-l", "-w"]
    for tok in tokens:
        parts += ["-e", _sh_quote(tok)]
    parts.append(scope)
    return " ".join(parts) + " | sort"


def _sh_quote(s: str) -> str:
    if all(c.isalnum() or c in "_-/." for c in s):
        return f"'{s}'"
    return "'" + s.replace("'", "'\\''") + "'"


# ---------------------------------------------------------------------------
# Pattern + jsonl row builders
# ---------------------------------------------------------------------------


def build_pattern(expected: list[str]) -> str:
    """Anchored regex matching exactly `\\n`-joined paths with optional trailing newline."""
    escaped = [p.replace(".", r"\.") for p in expected]
    body = r"\n".join(escaped)
    return rf"\A{body}\n?\Z"


def sorted_joined(expected: list[str], trailing_newline: bool = True) -> str:
    content = "\n".join(expected)
    return content + "\n" if trailing_newline else content


def build_prompt(tokens: list[str], scope: str) -> str:
    tok_list = ", ".join(f"`{t}`" for t in tokens)
    return (
        f"In this `requests` checkout, identify every file under `{scope}` "
        f"whose contents contain any of the following identifiers as a "
        f"whole word, case-sensitive: {tok_list}. Write your answer to "
        f"`location.txt` at the repo root, one repo-relative path per line "
        f"(e.g. `{scope}foo.py`), sorted lexicographically with Python's "
        f"default string ordering, with no blank lines, comments, or extra "
        f"whitespace. Do not modify any other files. "
        f"\n\n"
        f"The expected answer is defined as the exact output of the "
        f"canonical generator:\n\n"
        f"    {canonical_generator_cmd(scope, tokens)}\n\n"
        f"run from the repo root. You may verify your answer by running "
        f"this command yourself."
    )


def build_row(entry: dict[str, Any], expected: list[str]) -> dict[str, Any]:
    pattern = build_pattern(expected)
    desc = (
        f"location.txt must list exactly {{{', '.join(Path(p).name for p in expected)}}} "
        "as repo-relative paths, sorted alphabetically, one per line"
    )
    return {
        "id": entry["id"],
        "version": "v1",
        "repo": "requests",
        "name": entry["name"],
        "category": "code_localization",
        "contract": "completion",
        "surface": "tools",
        "min_calls": 2,
        "prompt": build_prompt(entry["tokens"], entry["scope"]),
        "checks": [
            {
                "type": "file_regex_disk",
                "path": "location.txt",
                "pattern": pattern,
                "description": desc,
            },
            {"type": "call_schema_valid"},
        ],
    }


# ---------------------------------------------------------------------------
# Spec rendering
# ---------------------------------------------------------------------------


SPEC_TEMPLATE = """\
# v1 #{sid} {name}

## Category

code_localization

## Contract

completion

## Surface

tools

## Repo

`requests` — psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Scope: `{scope}`
- Match semantics: whole word, case-sensitive (rg's `-w` flag, default case)
- Tokens ({n_tokens}):

{tokens_listing}

- Canonical generator (run from the workspace root):

```
$ {generator}
```

## Ground truth (F*)

Output of the canonical generator against pin `{pin_short}`, exactly {n_files} files, sorted lexicographically:

{expected_listing}

## Setup

The per-run fixture is a pinned copy of `psf/requests`. The agent writes a single deliverable — `location.txt` — at the root of the per-run workspace. No other files may be modified (scored indirectly by `call_schema_valid` catching malformed `write`/`edit` args).

## Prompt

> {prompt_blockquote}

## Pass criteria (2 checks)

1. `file_regex_disk` `location.txt` — anchored regex `\\A<path1>\\n<path2>\\n...\\n?\\Z` over the sorted F*. File content must be byte-equal to the sorted list, newline-joined, optional trailing newline.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**2 tool calls** minimum: one `bash`/`grep` invocation to run the canonical generator (or equivalent), plus one `write` of `location.txt`. Any agent that faithfully executes the criterion passes; there is no judgment call.

## Fail modes

- Omits a file that `rg -l -w -e <token>` would include (e.g. because the agent searched without `-w` and missed a token that only appears as a whole word, or scoped the search to the wrong directory) — anchored regex fails on set inequality.
- Adds a file the criterion does not include (e.g. a test module, a file matching only a substring of a token) — anchored regex fails.
- Correct files, wrong order — regex is anchored and order-sensitive, fails.
- Malformed `write` args (e.g. `path` instead of `filePath`) — `call_schema_valid` fails even if the file content is correct.

## Intentionally *not* checked

- Free-form explanation in the response text — only the `location.txt` artifact is scored.
- Which tools the agent uses to explore — `grep` / `read` / `glob` / `bash` are all acceptable as long as the final `location.txt` matches the criterion output and every tool call validates.

## Note on methodology

This sample defines F* **mechanically** as the output of an `rg` command over a fixed scope against a pinned SHA. It is a deliberate simplification of semantic file-level localization (`arXiv:2604.05013`), adopted to eliminate prompt-level interpretation ambiguity — any dispute over F* is settled in one line by re-running the canonical generator. The task therefore tests precise-criterion comprehension, effective search, and exact output formatting rather than subjective "participates in subsystem X" judgments.
"""


def render_spec(entry: dict[str, Any], expected: list[str], pin_short: str) -> str:
    scope = entry["scope"]
    tokens = entry["tokens"]
    generator = canonical_generator_cmd(scope, tokens)
    tokens_listing = "\n".join(f"  - `{t}`" for t in tokens)
    expected_listing = "\n".join(f"- `{p}`" for p in expected)
    prompt = build_prompt(tokens, scope)
    # Single-line-ish blockquote: keep newlines but prefix with `> ` on each line.
    prompt_blockquote = prompt.replace("\n", "\n> ")
    return SPEC_TEMPLATE.format(
        sid=entry["id"],
        name=entry["name"],
        scope=scope,
        n_tokens=len(tokens),
        tokens_listing=tokens_listing,
        generator=generator,
        pin_short=pin_short,
        n_files=len(expected),
        expected_listing=expected_listing,
        prompt_blockquote=prompt_blockquote,
    )


# ---------------------------------------------------------------------------
# File rewrite helpers
# ---------------------------------------------------------------------------


def rewrite_specs(
    entries_with_f_star: list[tuple[dict[str, Any], list[str]]],
    pin_short: str,
    dry_run: bool,
) -> None:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    keep_paths = set()
    for entry, expected in entries_with_f_star:
        sid = entry["id"]
        name = entry["name"]
        spec_path = SPEC_DIR / f"{sid:03d}_{name}.md"
        content = render_spec(entry, expected, pin_short)
        keep_paths.add(spec_path)
        if dry_run:
            print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(content)} bytes)")
            continue
        spec_path.write_text(content)
        print(f"  wrote {spec_path.relative_to(ROOT)} ({len(content)} bytes)")

    # Delete stale specs for ids 21..30 that no longer match the current manifest name.
    ids_in_manifest = {e["id"] for e, _ in entries_with_f_star}
    for stale in sorted(SPEC_DIR.glob("0[23]?_*.md")):
        try:
            stale_id = int(stale.name[:3])
        except ValueError:
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


def rewrite_jsonl(
    entries_with_f_star: list[tuple[dict[str, Any], list[str]]],
    dry_run: bool,
) -> None:
    new_rows_by_id: dict[int, dict[str, Any]] = {
        e["id"]: build_row(e, expected) for e, expected in entries_with_f_star
    }

    out_lines: list[str] = []
    seen_localization_ids: set[int] = set()
    with SAMPLES_JSONL.open() as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                out_lines.append(raw.rstrip("\n"))
                continue
            s = json.loads(line)
            if s.get("category") == "code_localization" and s.get("id") in new_rows_by_id:
                sid = s["id"]
                if sid in seen_localization_ids:
                    raise RuntimeError(f"duplicate code_localization row for id {sid}")
                seen_localization_ids.add(sid)
                out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))
            else:
                out_lines.append(line)

    missing = set(new_rows_by_id) - seen_localization_ids
    if missing:
        raise RuntimeError(
            f"manifest has ids {sorted(missing)} but samples_v1.jsonl has no matching rows; "
            f"aborting to avoid silently appending (add placeholder rows first)"
        )

    new_content = "\n".join(out_lines) + "\n"

    if dry_run:
        print(f"  [dry-run] would write {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_content)} bytes, {len(out_lines)} rows)")
        return

    SAMPLES_JSONL.write_text(new_content)
    print(f"  wrote {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_content)} bytes, {len(out_lines)} rows)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _pin_short() -> str:
    try:
        repos = json.loads((ROOT / "data" / "v1_repos.json").read_text())
        sha = repos.get("requests", {}).get("pin") or ""
        return sha[:12] if sha else "unknown"
    except (json.JSONDecodeError, OSError):
        return "unknown"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="print plan, don't write")
    p.add_argument("--id", type=int, action="append", help="limit to these sample ids (others unchanged)")
    args = p.parse_args()

    manifest = load_manifest()
    samples = manifest.get("samples", [])
    if not samples:
        print("ERROR: manifest has no 'samples' list", file=sys.stderr)
        return 2

    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]
        if len(samples) != len(wanted):
            print(
                f"ERROR: requested ids {sorted(wanted)} but manifest has "
                f"{[s['id'] for s in samples]}",
                file=sys.stderr,
            )
            return 2

    print("=" * 60)
    print("Computing F* for each sample")
    print("=" * 60)

    entries_with_f_star: list[tuple[dict[str, Any], list[str]]] = []
    any_short = False
    for entry in samples:
        sid = entry["id"]
        if entry.get("type") == "structured_output":
            print(
                f"  #{sid} {entry['name']}: SKIP (type=structured_output; "
                f"managed by data/scripts/derive_021_ground_truth.py)"
            )
            continue
        scope = entry["scope"]
        tokens = entry["tokens"]
        f_star = compute_f_star(scope, tokens)
        # Verify every path exists in the submodule (guards against manifest scope drift).
        for rel in f_star:
            if not (V1_REQUESTS_ROOT / rel).is_file():
                print(f"  ERROR: #{sid} returned non-file path {rel!r}", file=sys.stderr)
                return 2
        status = "ok" if len(f_star) >= MIN_FILES else "TOO SHORT"
        print(f"  #{sid} {entry['name']}: {len(f_star)} files [{status}]")
        for rel in f_star:
            print(f"      {rel}")
        if len(f_star) < MIN_FILES:
            any_short = True
            print(
                f"    -> |F*|={len(f_star)} is below MIN_FILES={MIN_FILES}; widen tokens and re-run.",
                file=sys.stderr,
            )
        entries_with_f_star.append((entry, f_star))

    if any_short:
        print()
        print("RESULT: FAIL (one or more samples have |F*| < 5)")
        return 1

    print()
    print("=" * 60)
    print("Writing spec files")
    print("=" * 60)
    rewrite_specs(entries_with_f_star, _pin_short(), args.dry_run)

    print()
    print("=" * 60)
    print("Rewriting data/samples_v1.jsonl")
    print("=" * 60)
    rewrite_jsonl(entries_with_f_star, args.dry_run)

    print()
    print("=" * 60)
    if args.dry_run:
        print("RESULT: DRY-RUN OK (no files written)")
    else:
        print(f"RESULT: OK ({len(entries_with_f_star)} samples regenerated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
