#!/usr/bin/env python3
"""
Regenerate v1 structured-output localization samples (#21-#30) from
`data/v1_localization_criteria.json`.

For each entry this script:

    1. Runs `scripts.localization_oracle.anchor_and_callers` (T1) or
       `callers_of_set` (T2) against the pinned submodule, applying the
       per-sample rg cross-check and (for #21) module-level uniqueness.
    2. Renders a natural-language prompt from a shared template, substituting
       the per-sample anchor/target/scope description strings stored in the
       manifest.
    3. Rewrites `data/specs/v1/<NNN>_<name>.md` with the standard v3c spec
       layout (difficulty tier, structural signature, gold answer, SHA-256,
       five-layer verification note, fail modes).
    4. Rewrites the corresponding row in `data/samples_v1.jsonl` with the
       new prompt, anchored regex pattern, `difficulty`, and
       `structural_signature` fields. `min_calls` is always 2.
    5. Deletes any stale spec files whose filename no longer matches the
       manifest (e.g. #26's rename from `request_prep` to `hook_dispatch`).

The script is idempotent: two runs against the same submodule pin + manifest
produce byte-identical outputs.

Usage
-----
    python3 data/scripts/regen_structured_samples.py
    python3 data/scripts/regen_structured_samples.py --dry-run
    python3 data/scripts/regen_structured_samples.py --id 21 --id 27
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.scripts.localization_oracle import (  # noqa: E402
    anchor_and_callers,
    build_pattern,
    callers_of_set,
    check_module_level_uniqueness,
    cross_check_rg_calls,
    cross_check_rg_calls_t2,
    emit_gold,
    result_to_dict,
    sha256_gold,
    submodule_head_sha,
)

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_localization_criteria.json"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def derive(entry: dict[str, Any]):
    """Run the oracle for a single manifest entry and return (result, template)."""
    tmpl = entry["template"]
    if tmpl == "T1":
        anchor = entry["anchor"]
        scope = entry["scope"]
        result = anchor_and_callers(
            anchor_file=anchor["file"],
            anchor_name=anchor["name"],
            scope=scope,
            require_module_level_anchor=bool(anchor.get("module_level", True)),
        )
        cross_check_rg_calls(result.scope_files, anchor["name"], result.call_sites)
        if entry["id"] == 21:
            check_module_level_uniqueness(
                anchor["file"], "merge_", [anchor["name"]]
            )
        return result, tmpl
    if tmpl == "T2":
        result = callers_of_set(
            targets=entry["targets"],
            scope=entry["scope"],
            exclude_target_defs=True,
        )
        cross_check_rg_calls_t2(result)
        return result, tmpl
    raise ValueError(f"unknown template {tmpl!r} on sample {entry['id']}")


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


QUALNAME_RULES = (
    "Each line is `file_path::QualifiedName` — repo-relative path followed by `::` "
    "and the dotted qualified name of the function. Module-level functions use "
    "their bare name (e.g. `merge_cookies`); methods on classes or mixins use "
    "`ClassName.method` (e.g. `Session.prepare_request`); nested closures use "
    "`outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` "
    "is written `Response.iter_content.generate`). End with a single trailing newline."
)


def render_prompt(entry: dict[str, Any]) -> str:
    domain = entry["prompt_domain"].rstrip(".")
    if entry["template"] == "T1":
        return (
            f"In this `requests` checkout, {domain}.\n\n"
            f"Write `location.txt` at the repo root listing, one per line in "
            f"lexicographic order, every function matching either:\n\n"
            f"- {entry['prompt_anchor_description']}, or\n"
            f"- {entry['prompt_scope_description']}.\n\n"
            f"{QUALNAME_RULES}"
        )
    # T2
    return (
        f"In this `requests` checkout, {domain}.\n\n"
        f"Write `location.txt` at the repo root listing, one per line in "
        f"lexicographic order, every function defined anywhere under "
        f"`src/requests/` (any nesting depth, including methods on classes, "
        f"mixins, and nested closures) whose body contains a direct call "
        f"resolving by name to {entry['prompt_target_description']}. Both "
        f"bare-name calls (`X(...)`) and attribute calls (`self.X(...)`, "
        f"`obj.X(...)`) count. Lines that only import or re-export those "
        f"names do not count.\n\n"
        f"**Nested defs.** A call site physically inside a nested `def` "
        f"(closure, inner helper) counts toward the enclosing function too — "
        f"the enclosing function lexically contains that call site. The "
        f"nested function is *also* a separate entry in its own right. So "
        f"if a helper `generate` defined inside `Response.iter_content` "
        f"contains a matching call, both `Response.iter_content` and "
        f"`Response.iter_content.generate` appear in the answer.\n\n"
        f"**Exclusion by name.** Any function whose own unqualified name "
        f"equals one of the target names is excluded from the answer, "
        f"regardless of the class or module it is defined on. The target "
        f"names for this sample are the unqualified names listed above "
        f"(e.g. `close`, not `Session.close`); a function literally named "
        f"`close` on *any* class is therefore never in the answer, even if "
        f"its body contains a matching attribute call like "
        f"`adapter.close()`.\n\n"
        f"{QUALNAME_RULES}"
    )


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

## Difficulty tier

**{difficulty}**. See `data/v1_localization_criteria.json` for the full tier-diversity matrix covering all 10 v3c structured samples.

## Structural signature

```
{structural_signature_block}
```

No other v3c sample in this tier shares this exact signature. See the `convert_22-30_v3c_tiered` plan for the diversity argument.

## Design

{design_block}

## Ground truth (gold answer)

Derived mechanically by [data/scripts/derive_0{sid}_ground_truth.py](../../scripts/derive_0{sid}_ground_truth.py) against pin `{pin_short}`. {n_entries} entries, already in lexicographic order:

```text
{gold_listing}
```

SHA-256 of the gold string (with trailing newline): `{sha256}`.

## Five-layer verification

1. **AST derivation** via the shared [data/scripts/localization_oracle.py](../../scripts/localization_oracle.py) (`{template}` template). Every `FunctionDef` / `AsyncFunctionDef` in scope is walked; `ast.Call` nodes whose `func.id` or `func.attr` matches the anchor/target name produce the "direct call" relation.
2. **`rg` cross-check**: every AST-discovered call line must appear in `rg -n -w --with-filename <name> <scope_files>` output. Catches dynamic/meta-programming patterns or AST/rg drift.{extra_layer_3}
4. **Evaluator audit** via [data/scripts/audit_localization_structured.py](../../scripts/audit_localization_structured.py): Pass 1 (positive + negative `location.txt` variants through the real `file_regex_disk` evaluator) and Pass 2 (end-to-end `eval.evaluate()` with synthesized trace).
5. **Pilot panel** (post-locking): 5 models × 3 seeds; top-tier model must reach ≥ 2/3; per-tier pass-rate correlation matrix < 0.85 between any two samples in the same tier.

## Setup

The per-run fixture is a pinned copy of `psf/requests`. The agent writes a single deliverable — `location.txt` — at the root of the per-run workspace. No other files may be modified (enforced indirectly by `call_schema_valid` catching malformed `write`/`edit` args).

## Prompt

{prompt_blockquote}

## Pass criteria (2 checks)

1. `file_regex_disk` `location.txt` — anchored regex demanding the exact {n_entries}-line gold above, optional trailing newline. Any deviation (wrong function, wrong file, missing/added entry, wrong qualname style, wrong sort, extra content) fails.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**≥ 2 tool calls** in practice: at least one `grep`/`bash rg` (or equivalent) to locate the relevant functions with enough context to resolve enclosing class + nesting, plus one `write` of `location.txt`. Careful agents add `read` calls to confirm function boundaries but are not required to by the rubric.

## Known fail modes

- Wrong/missing entry (e.g. overlooks a mixin caller, picks the wrong anchor) — anchored regex fails.
- Class prefix dropped (e.g. `send` instead of `Session.send`) or added on a module-level function — regex fails.
- Nested closure missed (e.g. `Response.iter_content.generate` flattened to `generate` or to `iter_content.generate` without the outer class) — regex fails.
- Paths written without the `src/requests/` prefix, or with a leading `./` — regex fails.
- Entries out of lexicographic order — regex fails.
- Malformed `write` args (e.g. `path` instead of `filePath`) — `call_schema_valid` fails even if the content would have matched.

## Intentionally *not* checked

- Free-form explanation text — only `location.txt` is scored.
- Which tools the agent uses to explore (`read`, `grep`, `glob`, `bash rg`, etc.) — any mix that produces the exact gold passes.
- Whether the agent reasons about inheritance, lifecycle, or mixin resolution order — only the artifact matters.

## Note on methodology

This sample is part of the v3c family — a natural-language, structured-output localization task. It is a deliberate divergence from both `arXiv:2604.05013` (semantic file-level localization, too ambiguous) and the pre-v3c criterion-anchored design (mechanical but too easy — trivially solved by a single `rg -l -w`). The natural-language prompt stresses reading comprehension; the dotted-qualname discipline forces a search → read → write pipeline that still exercises opencode's tool-use surface (the agent must resolve which function each call site belongs to, which a single-shot `rg` cannot answer). Ground-truth determinism is preserved by the five-layer verification protocol above.

If the submodule pin changes, re-run the deriver and update the gold, the regex, and the SHA-256 here.

{theme_note}"""


def _design_block(entry: dict[str, Any]) -> str:
    sig = entry["structural_signature"]
    tmpl = entry["template"]
    if tmpl == "T1":
        anchor = entry["anchor"]
        return (
            f"Template **T1** (anchor + direct callers). The agent must identify\n\n"
            f"1. the anchor function (semantic description), and\n"
            f"2. every function under the given scope whose body contains a direct "
            f"call resolving by name to the anchor.\n\n"
            f"Anchor: `{anchor['file']}::{anchor['name']}` "
            f"(`{'module-level' if anchor.get('module_level') else 'method'}`).\n\n"
            f"Scope: `{entry['scope']}`.\n\n"
            f"Answer shape: {sig['answer_entries']} entries across "
            f"{sig['answer_files']} file(s). Unique structural trait: "
            f"`{sig['unique_trait']}`."
        )
    return (
        f"Template **T2** (callers of a set). The agent must identify every function "
        f"anywhere under the given scope whose body contains a direct call resolving "
        f"by name to any of the given target names. Two conventions applied by the "
        f"oracle and stated explicitly in the prompt:\n\n"
        f"- **Nested-def attribution**: a call site inside a nested `def` counts "
        f"toward the enclosing function too, and the nested def is itself a separate "
        f"entry (so both `outer` and `outer.inner` can appear in one answer).\n"
        f"- **Exclusion by name**: a function whose own unqualified name equals any "
        f"target name is excluded, regardless of enclosing class or module (so a "
        f"target `close` excludes every function literally named `close`, even on "
        f"unrelated classes).\n\n"
        f"Targets: {entry['targets']} (kind: `{sig['target_kind']}`).\n\n"
        f"Scope: `{entry['scope']}`.\n\n"
        f"Answer shape: {sig['answer_entries']} entries across "
        f"{sig['answer_files']} file(s). Unique structural trait: "
        f"`{sig['unique_trait']}`."
    )


def _pin_short() -> str:
    try:
        return submodule_head_sha()[:12]
    except Exception:
        return "unknown"


def render_spec(entry: dict[str, Any], result, gold: str, pattern: str, digest: str) -> str:
    prompt = render_prompt(entry)
    prompt_blockquote = "\n".join(f"> {line}" if line.strip() else ">" for line in prompt.split("\n"))

    sig_block = json.dumps(entry["structural_signature"], indent=2)

    if entry["template"] == "T1":
        extra = (
            "\n3. **Anchor-kind assertion**: the oracle asserts exactly one "
            f"`{entry['anchor']['name']}` definition matching the declared "
            f"`module_level={entry['anchor'].get('module_level', True)}` kind in "
            f"`{entry['anchor']['file']}`, with no decorators, before emitting gold."
        )
        if entry["id"] == 21:
            extra += (
                " Additionally, `merge_cookies` is asserted to be the only "
                "module-level `merge_*` function in `cookies.py`."
            )
    else:
        extra = (
            "\n3. **Per-target cross-check**: a separate `rg` pass is run for each "
            f"target name in `{entry['targets']}`; every per-target AST call site "
            "must appear in its rg output."
        )

    gold_listing = gold.rstrip("\n")

    theme_note = ""
    if "_theme_migration_note" in entry:
        theme_note = f"\n## Theme migration note\n\n{entry['_theme_migration_note']}\n"

    return SPEC_TEMPLATE.format(
        sid=entry["id"],
        name=entry["name"],
        difficulty=entry["difficulty"],
        structural_signature_block=sig_block,
        design_block=_design_block(entry),
        pin_short=_pin_short(),
        n_entries=len(result.entries),
        gold_listing=gold_listing,
        sha256=digest,
        template=entry["template"],
        extra_layer_3=extra,
        prompt_blockquote=prompt_blockquote,
        theme_note=theme_note,
    )


# ---------------------------------------------------------------------------
# JSONL row rendering
# ---------------------------------------------------------------------------


def build_row(entry: dict[str, Any], result, prompt: str, pattern: str) -> dict[str, Any]:
    desc = (
        f"location.txt must list exactly the {len(result.entries)} gold "
        f"`file::QualifiedName` entries, in lexicographic order, one per line"
    )
    return {
        "id": entry["id"],
        "version": "v1",
        "repo": "requests",
        "name": entry["name"],
        "category": "code_localization",
        "contract": "completion",
        "surface": "tools",
        "type": "structured_output",
        "difficulty": entry["difficulty"],
        "structural_signature": entry["structural_signature"],
        "min_calls": 2,
        "prompt": prompt,
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
# Rewrite helpers
# ---------------------------------------------------------------------------


def rewrite_specs(
    payloads: list[tuple[dict[str, Any], Any, str]],
    *,
    dry_run: bool,
) -> None:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    keep_paths: set[Path] = set()
    for entry, result, spec_text in payloads:
        sid = entry["id"]
        spec_path = SPEC_DIR / f"{sid:03d}_{entry['name']}.md"
        keep_paths.add(spec_path)
        if dry_run:
            print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(spec_text)} bytes)")
            continue
        spec_path.write_text(spec_text)
        print(f"  wrote {spec_path.relative_to(ROOT)} ({len(spec_text)} bytes)")

    sids = {e["id"] for e, _, _ in payloads}
    for stale in sorted(SPEC_DIR.glob("0[2-5]?_*.md")):
        try:
            stale_id = int(stale.name[:3])
        except ValueError:
            continue
        if stale_id not in sids:
            continue
        if stale in keep_paths:
            continue
        if dry_run:
            print(f"  [dry-run] would delete stale spec {stale.relative_to(ROOT)}")
        else:
            stale.unlink()
            print(f"  deleted stale spec {stale.relative_to(ROOT)}")


def rewrite_jsonl(rows_by_id: dict[int, dict[str, Any]], *, dry_run: bool) -> None:
    out_lines: list[str] = []
    seen: set[int] = set()
    with SAMPLES_JSONL.open() as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                out_lines.append(line)
                continue
            obj = json.loads(line)
            if obj.get("category") == "code_localization" and obj.get("id") in rows_by_id:
                sid = obj["id"]
                if sid in seen:
                    raise RuntimeError(f"duplicate code_localization row for id {sid}")
                seen.add(sid)
                out_lines.append(json.dumps(rows_by_id[sid], ensure_ascii=False))
            else:
                out_lines.append(line)

    # Any manifest ids that were not yet in the jsonl file get appended at the
    # end (sorted by id). This supports adding new samples without having to
    # hand-edit samples_v1.jsonl first.
    missing = sorted(set(rows_by_id) - seen)
    for sid in missing:
        out_lines.append(json.dumps(rows_by_id[sid], ensure_ascii=False))

    new_content = "\n".join(out_lines) + "\n"
    if dry_run:
        print(f"  [dry-run] would write {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_content)} bytes, {len(out_lines)} rows)")
        return
    SAMPLES_JSONL.write_text(new_content)
    print(f"  wrote {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_content)} bytes, {len(out_lines)} rows)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--id", type=int, action="append")
    args = p.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text())
    samples = manifest.get("samples", [])
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]
        if len(samples) != len(wanted):
            print(f"ERROR: requested ids {sorted(wanted)} but manifest has {[s['id'] for s in samples]}")
            return 2

    payloads: list[tuple[dict[str, Any], Any, str]] = []
    rows_by_id: dict[int, dict[str, Any]] = {}

    print("=" * 60)
    print("Deriving ground truth via oracle")
    print("=" * 60)
    for entry in samples:
        sid = entry["id"]
        result, tmpl = derive(entry)
        gold = emit_gold(result.entries)
        pattern = build_pattern(gold)
        digest = sha256_gold(gold)
        prompt = render_prompt(entry)
        spec = render_spec(entry, result, gold, pattern, digest)
        row = build_row(entry, result, prompt, pattern)
        payloads.append((entry, result, spec))
        rows_by_id[sid] = row
        sig = entry["structural_signature"]
        print(
            f"  #{sid} {entry['name']} [{entry['difficulty']:6}] "
            f"{tmpl}  entries={len(result.entries)}/files={sig['answer_files']}  "
            f"sha={digest[:12]}..."
        )

    print()
    print("=" * 60)
    print("Writing spec files")
    print("=" * 60)
    rewrite_specs(payloads, dry_run=args.dry_run)

    print()
    print("=" * 60)
    print("Rewriting data/samples_v1.jsonl")
    print("=" * 60)
    rewrite_jsonl(rows_by_id, dry_run=args.dry_run)

    print()
    print("=" * 60)
    if args.dry_run:
        print("RESULT: DRY-RUN OK (no files written)")
    else:
        print(f"RESULT: OK ({len(payloads)} structured samples regenerated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
