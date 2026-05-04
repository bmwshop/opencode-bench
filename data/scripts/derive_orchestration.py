#!/usr/bin/env python3
"""
Compose runnable v1 orchestration sample rows from
data/v1_orchestration_criteria.json.

Each manifest entry is self-contained: it declares its own prompt, checks,
repo, and pattern. derive composes the JSONL row by:

  1. Setting `category: orchestration` on the row.
  2. Setting `version: v1` and `repo: <manifest.repo>`.
  3. Materializing any `workspace_overlay` files under
     projects/v1/orchestration/<NNN>/ (mirrors the mutants overlay scheme).
  4. Rendering data/specs/v1/<NNN>_<name>.md.
  5. Replacing or appending the row in data/samples_v1.jsonl.

Usage
-----
    python3 data/scripts/derive_orchestration.py            # regenerate everything
    python3 data/scripts/derive_orchestration.py --dry-run  # print plan, no writes
    python3 data/scripts/derive_orchestration.py --id 301   # one sample only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import PROJECTS  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "v1_orchestration_criteria.json"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
OVERLAY_ROOT = PROJECTS / "v1" / "orchestration"

ORCH_ID_LOW = 301
ORCH_ID_HIGH = 330
ORCH_CATEGORY = "orchestration"

VALID_PATTERNS = {"parallel_dispatch", "chain", "dag_join", "iteration", "merge"}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def materialize_overlay(sid: int, overlay: dict[str, str], dry_run: bool) -> Path:
    target = OVERLAY_ROOT / f"{sid:03d}"
    if not overlay:
        # Even with no overlay files, leave the dir empty rather than absent
        # so run.py's overlay merge step has a stable target. Optional.
        return target
    if dry_run:
        for rel, content in overlay.items():
            print(f"  [dry-run] would write {(target / rel).relative_to(ROOT)} ({len(content)} bytes)")
        return target
    if target.exists():
        for old in sorted(target.rglob("*"), reverse=True):
            if old.is_file():
                old.unlink()
            elif old.is_dir() and old != target:
                try:
                    old.rmdir()
                except OSError:
                    pass
    target.mkdir(parents=True, exist_ok=True)
    for rel, content in overlay.items():
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content)
    return target


def build_row(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "version": "v1",
        "repo": entry["repo"],
        "name": entry["name"],
        "category": ORCH_CATEGORY,
        "contract": entry.get("contract", "completion"),
        "surface": entry.get("surface", "tools"),
        "min_calls": entry.get("min_calls", 3),
        "pattern": entry["pattern"],
        "prescription_form": entry.get("prescription_form", "prescriptive"),
        "prompt": entry["prompt"],
        "checks": list(entry["checks"]),
    }


SPEC_TEMPLATE = """# v1 #{sid} {name}

## Category

orchestration

## Pattern

`{pattern}` ({prescription_form})

## Repo

`{repo}` (pinned via `data/v1_repos.json`).

## Prompt

> {prompt_blockquote}

## Pass criteria ({n_checks} checks)

{checks_table}

## Why this sample

{why_blurb}

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
"""

WHY_BLURBS = {
    "parallel_dispatch": "Tests whether the model dispatches multiple tool/subagent calls in a single assistant turn (parallel-dispatch behavior). The `parallel_dispatch_count` verifier requires the prescribed N calls to share one step_start/step_finish boundary.",
    "chain": "Tests whether the model emits a strictly ordered multi-step plan, with each step's output (or implicit context) flowing to the next. The `tool_call_sequence` and `tool_call_count` verifiers pin both the order and the cardinality.",
    "dag_join": "Tests parallel reads of independent inputs converging into a single output artifact. Combines parallel dispatch with output aggregation.",
    "iteration": "Tests bounded for-each-over-prescribed-list behavior. The model must issue exactly N calls (one per item), in the specified order, then aggregate.",
    "merge": "Tests subagent dispatch + reconciliation: multiple subagents return overlapping or related facts; the parent must merge them into a single deliverable.",
}


def render_spec(entry: dict, row: dict) -> str:
    lines = ["| # | type | description |", "|---|------|-------------|"]
    for i, c in enumerate(row["checks"], 1):
        desc = c.get("description", "_(no description)_").replace("|", "\\|")
        lines.append(f"| {i} | `{c['type']}` | {desc} |")
    return SPEC_TEMPLATE.format(
        sid=row["id"],
        name=row["name"],
        pattern=row["pattern"],
        prescription_form=row["prescription_form"],
        repo=row["repo"],
        prompt_blockquote=row["prompt"].replace("\n", "\n> "),
        n_checks=len(row["checks"]),
        checks_table="\n".join(lines),
        why_blurb=WHY_BLURBS.get(row["pattern"], "(no description)"),
    )


def write_spec(row: dict, content: str, dry_run: bool) -> None:
    spec_path = SPEC_DIR / f"{row['id']:03d}_{row['name']}.md"
    if dry_run:
        print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(content)} bytes)")
        return
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(content)
    print(f"  wrote {spec_path.relative_to(ROOT)} ({len(content)} bytes)")


def rewrite_jsonl(new_rows_by_id: dict[int, dict], dry_run: bool, prune_unrelated: bool) -> None:
    edit_ids = set(new_rows_by_id)
    out_lines: list[str] = []
    seen_ids: set[int] = set()
    existing = SAMPLES_JSONL.read_text().splitlines() if SAMPLES_JSONL.exists() else []

    for raw in existing:
        line = raw.rstrip("\n")
        if not line.strip():
            out_lines.append(line)
            continue
        s = json.loads(line)
        sid = s.get("id")
        if sid in edit_ids:
            if sid in seen_ids:
                raise RuntimeError(f"duplicate row for id {sid}")
            seen_ids.add(sid)
            out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))
        elif (
            prune_unrelated
            and s.get("category") == ORCH_CATEGORY
            and ORCH_ID_LOW <= (sid or 0) <= ORCH_ID_HIGH
            and sid not in edit_ids
        ):
            print(f"  pruning stale orchestration row #{sid} (not in current manifest)")
            continue
        else:
            out_lines.append(line)

    for sid in sorted(edit_ids - seen_ids):
        out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))

    new_content = "\n".join(out_lines) + "\n"
    if dry_run:
        print(f"  [dry-run] would write {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_content)} bytes, {len(out_lines)} rows)")
        return
    SAMPLES_JSONL.write_text(new_content)
    print(f"  wrote {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_content)} bytes, {len(out_lines)} rows)")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--id", type=int, action="append")
    args = p.parse_args()

    manifest = load_manifest()
    samples = manifest.get("samples", [])
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]
        missing = wanted - {s["id"] for s in samples}
        if missing:
            print(f"ERROR: manifest missing ids {sorted(missing)}", file=sys.stderr)
            return 2

    print("=" * 60)
    print("Composing orchestration rows")
    print("=" * 60)

    new_rows: dict[int, dict] = {}
    any_error = False
    for entry in samples:
        sid = entry["id"]
        name = entry["name"]
        if not (ORCH_ID_LOW <= sid <= ORCH_ID_HIGH):
            print(f"  FAIL #{sid} {name}: id out of range [{ORCH_ID_LOW}, {ORCH_ID_HIGH}]")
            any_error = True
            continue
        if entry.get("pattern") not in VALID_PATTERNS:
            print(f"  FAIL #{sid} {name}: invalid pattern {entry.get('pattern')!r}")
            any_error = True
            continue
        try:
            overlay = entry.get("workspace_overlay", {}) or {}
            materialize_overlay(sid, overlay, args.dry_run)
            row = build_row(entry)
            spec_content = render_spec(entry, row)
            write_spec(row, spec_content, args.dry_run)
            new_rows[sid] = row
            print(f"  PASS #{sid} {name}  (pattern={entry['pattern']}, repo={entry['repo']})")
        except Exception as e:
            print(f"  FAIL #{sid} {name}: {type(e).__name__}: {e}")
            any_error = True

    if any_error:
        print("\nRESULT: FAIL")
        return 1

    print()
    print("=" * 60)
    print("Rewriting data/samples_v1.jsonl (orchestration rows)")
    print("=" * 60)
    rewrite_jsonl(new_rows, args.dry_run, prune_unrelated=not bool(args.id))

    print()
    print("=" * 60)
    if args.dry_run:
        print("RESULT: DRY-RUN OK")
    else:
        print(f"RESULT: OK ({len(new_rows)} orchestration samples composed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
