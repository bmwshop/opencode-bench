#!/usr/bin/env python3
"""
Compose runnable tool-restriction mutant rows from
data/v1_mutant_criteria.json.

Each mutant inherits its parent's task content (prompt, repo, base checks)
and layers in:

  1. A workspace overlay under projects/v1/mutants/<NN>/ (one or more of
     AGENTS.md, opencode.json, .opencode/agents/main.md).
  2. Extra checks declared by the manifest entry (the restriction-honored
     verifier set: e.g. `no_tool_name_recursive` for the denied tool plus
     `call_schema_valid`, which is recursive-aware when given a trace).

Output artifacts:

  - projects/v1/mutants/<NN>/...         (workspace overlay files)
  - data/specs/v1/<NN>_<name>.md         (human-readable spec)
  - data/samples_v1.jsonl row id=<NN>    (runnable row, replaces or
                                          appends as needed)

The composer is idempotent: re-running it rewrites the artifacts in-place
without creating duplicates. Rows for ids in [201, 220] that are NOT
declared in the manifest get pruned from samples_v1.jsonl on each run, so
the manifest is the single source of truth.

Usage
-----
    python3 data/scripts/derive_mutants.py            # regenerate everything
    python3 data/scripts/derive_mutants.py --dry-run  # print plan, no writes
    python3 data/scripts/derive_mutants.py --id 201   # one mutant only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import PROJECTS  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_mutant_criteria.json"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
MUTANT_OVERLAY_ROOT = PROJECTS / "v1" / "mutants"

MUTANT_ID_LOW = 201
MUTANT_ID_HIGH = 230
# Runtime category describes what the sample tests (a tool restriction).
# The "mutant" provenance is encoded by parent_id + mutation_kind +
# mutation_source on each row; it doesn't need to be in the category name.
MUTANT_CATEGORY = "tool_restriction"
# Legacy category value (pre-rename); pruned by `rewrite_jsonl` so stale
# rows don't accumulate when the category is changed.
MUTANT_CATEGORY_LEGACY = {"tool_restriction_mutant"}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def load_parent_index(version: str = "v1") -> dict[int, dict[str, Any]]:
    """Read samples_v1.jsonl and return {id: row} for non-mutant rows."""
    out: dict[int, dict[str, Any]] = {}
    if not SAMPLES_JSONL.exists():
        return out
    for line in SAMPLES_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        cat = row.get("category")
        if cat == MUTANT_CATEGORY or cat in MUTANT_CATEGORY_LEGACY:
            continue
        if row.get("version", "v1") != version:
            continue
        out[row["id"]] = row
    return out


def materialize_overlay(mid: int, overlay: dict[str, str], dry_run: bool) -> Path:
    """Write the per-mutant overlay tree at projects/v1/mutants/<NNN>/."""
    target = MUTANT_OVERLAY_ROOT / f"{mid:03d}"
    if dry_run:
        for rel, content in overlay.items():
            dst = target / rel
            print(f"  [dry-run] would write {dst.relative_to(ROOT)} ({len(content)} bytes)")
        return target
    if target.exists():
        # Remove stale overlay files (idempotency) before writing the fresh set.
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


def build_row(entry: dict, parent_row: dict) -> dict:
    """Compose the mutant's runnable row by inheriting from the parent and
    layering in mutant-specific fields and extra checks.

    Inheritance:
      - prompt, repo, contract, surface, min_calls   (verbatim)
      - checks                                       (parent checks first,
                                                      then mutant extra_checks)
    Overrides:
      - id, name                                     (mutant's own)
      - category                                     ("tool_restriction_mutant")
    Additions:
      - parent_id, mutation_kind                     (NEW fields)
    """
    parent_checks = list(parent_row.get("checks", []))
    extra = [dict(c) for c in entry.get("extra_checks", [])]

    # De-duplicate checks by (type + key fields). The parent's
    # `call_schema_valid` is the same evaluator the mutant declares (it
    # already recurses into subagents when a trace_path is supplied), so
    # the dedupe naturally collapses them into one row.
    seen_keys: set[tuple] = set()
    merged_checks: list[dict] = []
    for c in parent_checks + extra:
        key = (c.get("type"), c.get("equals") or c.get("not_equals") and tuple(c["not_equals"] if isinstance(c["not_equals"], list) else [c["not_equals"]]))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        merged_checks.append(c)

    row = {
        "id": entry["id"],
        "version": parent_row.get("version", "v1"),
        "repo": parent_row.get("repo", ""),
        "name": entry["name"],
        "category": MUTANT_CATEGORY,
        "contract": parent_row.get("contract", "completion"),
        "surface": parent_row.get("surface", "tools"),
        "min_calls": parent_row.get("min_calls", 3),
        "parent_id": entry["parent_id"],
        "parent_version": entry.get("parent_version", "v1"),
        "mutation_kind": entry["mutation_kind"],
        "mutation_source": entry.get("mutation_source", {}),
        "prompt": parent_row["prompt"],
        "checks": merged_checks,
    }
    # Persona-file mutants need `--agent <name>` on the opencode CLI to
    # actually activate the custom main agent (see v0 #2 custom_main_agent
    # for the working pattern). The manifest declares the name; run.py
    # already passes it through when "agent" is on the row.
    if "agent" in entry:
        row["agent"] = entry["agent"]
    # `superseded_before_run_ts` lets the analyzer ignore scored entries
    # from run dirs whose timestamp is < this cutoff -- used when a
    # methodology bug was found and rows had to be re-derived. Older runs
    # for that sample don't test what we currently claim and would
    # dilute the rerun signal if averaged in.
    if "superseded_before_run_ts" in entry:
        row["superseded_before_run_ts"] = entry["superseded_before_run_ts"]
    return row


SPEC_TEMPLATE = """# v1 #{sid} {name}

## Category

{category}

## Parent

This is a tool-restriction MUTANT of v1 #{parent_id} `{parent_name}` (`{parent_category}`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `{mutation_kind}`
- **source pattern**: borrowed from {mutation_source_str}
- **mechanism**: `{mechanism}`

{mechanism_blurb}

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

{overlay_files_block}

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> {prompt_blockquote}

## Pass criteria ({n_checks} checks)

{checks_table}

## Why this mutant

{why_blurb}

## Comparison points (panel-time)

The parent (`#{parent_id}` `{parent_name}`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the {plan_name} batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
"""


def _mechanism_blurb(kind: str) -> str:
    if kind.startswith("deny_") and kind.endswith("_system"):
        return (
            "Delivered through opencode's runtime permission layer "
            "(`opencode.json` `permission` block, modeled on v0 #22 "
            "`bash_strict`). Denied tools are hard-blocked: the model "
            "cannot call them at all -- attempts will be rejected by "
            "opencode before reaching the tool dispatcher."
        )
    if kind.startswith("agents_md_"):
        return (
            "Delivered through the workspace's `AGENTS.md` instruction "
            "file (modeled on v0 #12-#14 / #19). The denied tools remain "
            "*visible* in the model's tool list -- the restriction is "
            "instruction-based, so the verifier `no_tool_name_recursive` "
            "tests adherence rather than runtime blocking."
        )
    if kind.startswith("persona_main_"):
        return (
            "Delivered through opencode's custom main agent persona file "
            "(`.opencode/agents/main.md`, modeled on v0 #2 "
            "`custom_main_agent`). The persona's prompt instructs the "
            "model on tool-use policy. This is the *third* delivery "
            "mechanism for instruction-based restrictions -- a useful "
            "comparison point against the AGENTS.md-based variant of the "
            "same restriction on the same parent."
        )
    return "(unknown mechanism)"


def _why_blurb(kind: str) -> str:
    if kind == "deny_bash_system":
        return (
            "Tests whether the agent can solve the task using only native "
            "tools when shell access is hard-blocked. Different tasks have "
            "different bash dependence -- this measures it directly."
        )
    if kind == "deny_grep_system":
        return (
            "Tests whether the agent pivots to `bash rg` or pure `read` "
            "when the native grep tool is denied. Especially relevant for "
            "search-heavy tasks (localization)."
        )
    if kind == "deny_glob_system":
        return (
            "Tests whether the agent pivots to `bash find` or alternative "
            "discovery strategies when the native glob tool is denied."
        )
    if kind == "deny_read_system":
        return (
            "Tests whether the agent uses `bash cat` (or alternative "
            "shell-based file inspection) when the native read tool is "
            "denied. A genuine pivot is required because most edits "
            "require knowing the file's current content."
        )
    if kind == "deny_write_system":
        return (
            "Tests whether the agent uses `edit` (new-file mode) or "
            "`bash echo > file` to create deliverables when the native "
            "write tool is denied."
        )
    if kind == "deny_grep_and_glob_system":
        return (
            "Composite restriction: both native search tools blocked. "
            "Tests resilience under multi-tool stress."
        )
    if kind == "deny_full_system":
        return (
            "Classic v0 #22 `bash_strict` configuration: only `bash` is "
            "allowed; all other tools are denied. The agent must use "
            "shell commands for every operation."
        )
    if kind == "agents_md_bash_only":
        return (
            "AGENTS.md-based bash-only directive (the model could disobey, "
            "since other tools remain visible). Tests instruction "
            "adherence under tool-use restrictions."
        )
    if kind == "agents_md_no_grep_no_glob":
        return (
            "AGENTS.md forbids the native search tools but leaves bash + "
            "read available. Tests instruction adherence on a narrow "
            "two-tool prohibition."
        )
    if kind == "agents_md_no_bash":
        return (
            "AGENTS.md forbids bash; the agent must use only the native "
            "tools. Tests instruction adherence on a 'use native only' "
            "directive."
        )
    if kind == "agents_md_subagent_required":
        return (
            "AGENTS.md instructs the parent to delegate file reading to a "
            "subagent via the `task` tool. Tests subagent dispatch + "
            "consumption-of-subagent-output behavior under explicit "
            "delegation requirements."
        )
    if kind == "persona_main_bash_only":
        return (
            "Same restriction as the AGENTS.md-based bash-only mutant on "
            "the same parent, delivered through the custom main agent "
            "persona file. Comparison point for opencode's two "
            "instruction-delivery layers: does the persona-file path plumb "
            "the directive equally well as AGENTS.md?"
        )
    if kind == "persona_main_subagent_required":
        return (
            "Same restriction as the AGENTS.md-based subagent-required "
            "mutant on the same parent, delivered through the persona "
            "file. Comparison point for opencode's two instruction-"
            "delivery layers."
        )
    return "(no description)"


def _mechanism_for_kind(kind: str) -> str:
    if kind.endswith("_system"):
        return "opencode.json `permission`"
    if kind.startswith("agents_md_"):
        return "AGENTS.md"
    if kind.startswith("persona_main_"):
        return ".opencode/agents/main.md"
    return "unknown"


def _mutation_source_str(src: dict) -> str:
    return f"v0 #{src.get('id', '?')} (`{src.get('category', '?')}`)"


def render_spec(entry: dict, parent_row: dict, row: dict, overlay: dict[str, str]) -> str:
    overlay_files_block = "\n\n".join(
        f"### `{path}`\n\n```{('json' if path.endswith('.json') else ('markdown' if path.endswith('.md') else ''))}\n{content.rstrip()}\n```"
        for path, content in overlay.items()
    )
    if not overlay_files_block:
        overlay_files_block = "_(no workspace overlay files; restriction is verifier-only)_"

    checks_table_lines = ["| # | type | description |", "|---|------|-------------|"]
    for i, c in enumerate(row["checks"], 1):
        desc = c.get("description", "_(no description)_")
        # Escape pipe chars in description.
        desc = desc.replace("|", "\\|")
        checks_table_lines.append(f"| {i} | `{c['type']}` | {desc} |")

    return SPEC_TEMPLATE.format(
        sid=row["id"],
        name=row["name"],
        category=MUTANT_CATEGORY,
        parent_id=parent_row["id"],
        parent_name=parent_row["name"],
        parent_category=parent_row.get("category", "?"),
        mutation_kind=entry["mutation_kind"],
        mutation_source_str=_mutation_source_str(entry.get("mutation_source", {})),
        mechanism=_mechanism_for_kind(entry["mutation_kind"]),
        mechanism_blurb=_mechanism_blurb(entry["mutation_kind"]),
        overlay_files_block=overlay_files_block,
        prompt_blockquote=row["prompt"].replace("\n", "\n> "),
        n_checks=len(row["checks"]),
        checks_table="\n".join(checks_table_lines),
        why_blurb=_why_blurb(entry["mutation_kind"]),
        plan_name="v1 parents x v0 mutations",
    )


def write_spec(row: dict, content: str, dry_run: bool) -> None:
    spec_path = SPEC_DIR / f"{row['id']:03d}_{row['name']}.md"
    if dry_run:
        print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(content)} bytes)")
    else:
        SPEC_DIR.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(content)
        print(f"  wrote {spec_path.relative_to(ROOT)} ({len(content)} bytes)")


def rewrite_jsonl(
    new_rows_by_id: dict[int, dict],
    dry_run: bool,
    prune_unrelated: bool = True,
) -> None:
    """Replace mutant rows in samples_v1.jsonl in place; append new ones at the end.
    When `prune_unrelated=True`, also drop mutant rows whose ids are NOT in
    new_rows_by_id (full-manifest run). Set prune_unrelated=False when running
    against a subset (--id filter) so untouched mutants survive.
    """
    edit_ids = set(new_rows_by_id)
    out_lines: list[str] = []
    seen_ids: set[int] = set()
    existing = []
    if SAMPLES_JSONL.exists():
        existing = SAMPLES_JSONL.read_text().splitlines()

    for raw in existing:
        line = raw.rstrip("\n")
        if not line.strip():
            out_lines.append(line)
            continue
        s = json.loads(line)
        sid = s.get("id")
        if sid in edit_ids:
            if sid in seen_ids:
                raise RuntimeError(f"duplicate row for id {sid} in samples_v1.jsonl")
            seen_ids.add(sid)
            out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))
        elif (
            prune_unrelated
            and (s.get("category") == MUTANT_CATEGORY
                 or s.get("category") in MUTANT_CATEGORY_LEGACY)
            and MUTANT_ID_LOW <= (sid or 0) <= MUTANT_ID_HIGH
            and sid not in edit_ids
        ):
            print(f"  pruning stale mutant row #{sid} (not in current manifest)")
            continue
        else:
            out_lines.append(line)

    for sid in sorted(edit_ids - seen_ids):
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

    parent_index = load_parent_index()

    print("=" * 60)
    print("Composing mutant rows")
    print("=" * 60)

    new_rows: dict[int, dict] = {}
    any_error = False
    for entry in samples:
        sid = entry["id"]
        name = entry["name"]
        if not (MUTANT_ID_LOW <= sid <= MUTANT_ID_HIGH):
            print(
                f"  FAIL #{sid} {name}: id out of mutant range "
                f"[{MUTANT_ID_LOW}, {MUTANT_ID_HIGH}]"
            )
            any_error = True
            continue
        parent_id = entry.get("parent_id")
        if parent_id not in parent_index:
            print(
                f"  FAIL #{sid} {name}: parent #{parent_id} not found in samples_v1.jsonl"
            )
            any_error = True
            continue
        parent_row = parent_index[parent_id]
        try:
            overlay = entry.get("workspace_overlay", {}) or {}
            materialize_overlay(sid, overlay, args.dry_run)
            row = build_row(entry, parent_row)
            spec_content = render_spec(entry, parent_row, row, overlay)
            write_spec(row, spec_content, args.dry_run)
            new_rows[sid] = row
            print(
                f"  PASS #{sid} {name}  (parent #{parent_id} {parent_row['name']}, "
                f"kind={entry['mutation_kind']})"
            )
        except Exception as e:
            print(f"  FAIL #{sid} {name}: {type(e).__name__}: {e}")
            any_error = True

    if any_error:
        print()
        print("RESULT: FAIL (one or more mutants failed)")
        return 1

    print()
    print("=" * 60)
    print("Rewriting data/samples_v1.jsonl (mutant rows)")
    print("=" * 60)
    # Only prune unrelated mutant rows on a full-manifest run; with --id
    # we're touching a subset and unrelated rows must survive.
    rewrite_jsonl(new_rows, args.dry_run, prune_unrelated=not bool(args.id))

    print()
    print("=" * 60)
    if args.dry_run:
        print("RESULT: DRY-RUN OK (no files written)")
    else:
        print(f"RESULT: OK ({len(new_rows)} mutants composed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
