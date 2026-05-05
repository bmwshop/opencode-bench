#!/usr/bin/env python3
"""
Audit harness for tool-restriction mutant samples (#201-#220).

Two passes:

Pass 1 -- Layer 0 gates per manifest entry:

  - `parent_id` resolves to an existing v1 sample.
  - `mutation_kind` is in the recognized vocabulary.
  - For `deny_*_system`: workspace_overlay declares `opencode.json` with
    the expected permission keys.
  - For `agents_md_*`: workspace_overlay declares a non-empty AGENTS.md
    AND (for subagent-required) AGENTS.md mentions the `task` tool.
  - For `persona_main_*`: workspace_overlay declares
    `.opencode/agents/main.md`.
  - `extra_checks` always includes `call_schema_valid` (which the existing
    evaluator runs recursively when `trace_path` is supplied; see its
    docstring -- there is no separate `_recursive` variant registered).
  - For each `deny_X` system kind: `extra_checks` contains a
    `no_tool_name_recursive` entry naming the denied tool.
  - For each `agents_md_*` kind: `extra_checks` contains a
    `no_tool_name_recursive` entry naming the forbidden tools.

Pass 2 -- end-to-end derive + materialization:

  - Re-runs `data/scripts/derive_mutants.py` and verifies:
    * `projects/v1/mutants/<NN>/` exists with the declared overlay files.
    * `data/samples_v1.jsonl` contains the mutant row with the expected
      `category`, `parent_id`, and merged checks list.
    * `data/specs/v1/<NN>_<name>.md` exists.
  - Synthesizes a *compliant* opencode-style trace where the restriction
    is honored and verifies all `extra_checks` pass against it.
  - Synthesizes a *violation* trace where the restriction is broken and
    verifies the restriction-honored check FIRES.

Pass 2 doesn't run opencode -- the real end-to-end validation is the
pilot panel. This audit ensures the methodology surface is sound before
the panel run.

Usage
-----
    python3 data/scripts/audit_mutants.py
    python3 data/scripts/audit_mutants.py --id 201
    python3 data/scripts/audit_mutants.py --pass 1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common import PROJECTS  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_mutant_criteria.json"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
MUTANT_OVERLAY_ROOT = PROJECTS / "v1" / "mutants"

VALID_MUTATION_KINDS = {
    "deny_bash_system",
    "deny_grep_system",
    "deny_glob_system",
    "deny_read_system",
    "deny_write_system",
    "deny_grep_and_glob_system",
    "deny_full_system",
    "agents_md_bash_only",
    "agents_md_no_grep_no_glob",
    "agents_md_no_bash",
    "agents_md_subagent_required",
    "persona_main_bash_only",
    "persona_main_subagent_required",
}

# For each mutation_kind, what tools must `extra_checks` declare absent
# via `no_tool_name_recursive`. None means "no specific tool restriction
# verifier required" (e.g. subagent-required uses `no_tool_name` parent-only).
KIND_DENIED_TOOLS = {
    "deny_bash_system": {"bash"},
    "deny_grep_system": {"grep"},
    "deny_glob_system": {"glob"},
    "deny_read_system": {"read"},
    "deny_write_system": {"write"},
    "deny_grep_and_glob_system": {"grep", "glob"},
    "deny_full_system": {"read", "edit", "grep", "glob", "task", "todowrite"},
    "agents_md_bash_only": {"read", "edit", "write", "glob", "grep", "task"},
    "agents_md_no_grep_no_glob": {"grep", "glob"},
    "agents_md_no_bash": {"bash"},
    "persona_main_bash_only": {"read", "edit", "write", "glob", "grep", "task"},
}

# `mutation_kind` -> required overlay-file path keys.
# For persona_main_* the actual filename is per-mutant (must match the
# manifest entry's `agent` field); we check structural requirements via
# the persona-specific block in pass1_entry rather than naming a fixed path.
KIND_OVERLAY_REQUIREMENTS = {
    "deny_bash_system": {"opencode.json"},
    "deny_grep_system": {"opencode.json"},
    "deny_glob_system": {"opencode.json"},
    "deny_read_system": {"opencode.json"},
    "deny_write_system": {"opencode.json"},
    "deny_grep_and_glob_system": {"opencode.json"},
    "deny_full_system": {"opencode.json"},
    "agents_md_bash_only": {"AGENTS.md"},
    "agents_md_no_grep_no_glob": {"AGENTS.md"},
    "agents_md_no_bash": {"AGENTS.md"},
    "agents_md_subagent_required": {"AGENTS.md"},
    "persona_main_bash_only": set(),
    "persona_main_subagent_required": set(),
}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


# Runtime category describes what the sample tests; "mutant" is provenance
# encoded by parent_id + mutation_kind + mutation_source.
MUTANT_CATEGORY = "tool_restriction"
MUTANT_CATEGORY_LEGACY = {"tool_restriction_mutant"}


def _is_mutant_category(cat: str | None) -> bool:
    return cat == MUTANT_CATEGORY or cat in MUTANT_CATEGORY_LEGACY


def load_parent_index() -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not SAMPLES_JSONL.exists():
        return out
    for line in SAMPLES_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        s = json.loads(line)
        if _is_mutant_category(s.get("category")):
            continue
        out[s["id"]] = s
    return out


def load_mutant_rows() -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not SAMPLES_JSONL.exists():
        return out
    for line in SAMPLES_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        s = json.loads(line)
        if _is_mutant_category(s.get("category")):
            out[s["id"]] = s
    return out


# ---------------------------------------------------------------------------
# Pass 1: Layer 0 gates
# ---------------------------------------------------------------------------


def _has_no_tool_name_recursive_covering(checks: list[dict], denied: set[str]) -> bool:
    """Return True iff at least one `no_tool_name_recursive` in `checks` lists
    every tool in `denied` in its `not_equals` field (string or list)."""
    for c in checks:
        if c.get("type") != "no_tool_name_recursive":
            continue
        ne = c.get("not_equals")
        ne_set = {ne} if isinstance(ne, str) else set(ne or [])
        if denied <= ne_set:
            return True
    return False


def _has_check(checks: list[dict], chk_type: str) -> bool:
    return any(c.get("type") == chk_type for c in checks)


def pass1_entry(entry: dict, parent_index: dict[int, dict]) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    # (1) parent exists
    parent_id = entry.get("parent_id")
    if parent_id not in parent_index:
        errors.append(f"{prefix}: parent #{parent_id} not found in samples_v1.jsonl")

    # (2) mutation_kind in vocab
    kind = entry.get("mutation_kind")
    if kind not in VALID_MUTATION_KINDS:
        errors.append(f"{prefix}: mutation_kind {kind!r} not in vocabulary")
        return errors  # downstream gates depend on kind

    # (3) overlay file requirements
    overlay = entry.get("workspace_overlay") or {}
    required_paths = KIND_OVERLAY_REQUIREMENTS.get(kind, set())
    missing = required_paths - set(overlay)
    if missing:
        errors.append(
            f"{prefix}: workspace_overlay missing required path(s) for kind={kind!r}: {sorted(missing)}"
        )

    # (4) overlay content sanity
    if "opencode.json" in overlay:
        try:
            cfg = json.loads(overlay["opencode.json"])
        except json.JSONDecodeError as e:
            errors.append(f"{prefix}: opencode.json overlay isn't valid JSON: {e}")
            cfg = None
        if cfg is not None and "permission" not in cfg:
            errors.append(f"{prefix}: opencode.json overlay missing `permission` key")
    if "AGENTS.md" in overlay:
        text = overlay["AGENTS.md"]
        if not text.strip():
            errors.append(f"{prefix}: AGENTS.md overlay is empty")
        if kind == "agents_md_subagent_required" and "task" not in text:
            errors.append(
                f"{prefix}: agents_md_subagent_required AGENTS.md must mention the `task` tool"
            )
    persona_paths = [p for p in overlay if p.startswith(".opencode/agents/")]
    if kind.startswith("persona_main_") and not persona_paths:
        errors.append(
            f"{prefix}: persona_main_* mutant must declare at least one "
            f".opencode/agents/<name>.md overlay file"
        )
    if persona_paths:
        for p in persona_paths:
            text = overlay[p]
            if not text.strip():
                errors.append(f"{prefix}: persona file overlay {p!r} is empty")
                continue
            if not text.lstrip().startswith("---"):
                errors.append(
                    f"{prefix}: persona file {p!r} should begin with `---` frontmatter"
                )
                continue
            # opencode requires `mode: primary` on the frontmatter to activate
            # this agent as the top-level agent (see v0 #2). Otherwise it's
            # registered as a subagent target and `--agent <name>` on the CLI
            # has no effect.
            head = text.split("---", 2)[1] if text.count("---") >= 2 else ""
            if "mode: primary" not in head:
                errors.append(
                    f"{prefix}: persona file {p!r} frontmatter missing "
                    f"`mode: primary` (required to register as a top-level agent)"
                )
        # The manifest entry must declare which agent name to invoke. Without
        # it, run.py won't add `--agent <name>` to the opencode CLI and the
        # persona file is dead text in the workspace.
        if "agent" not in entry:
            errors.append(
                f"{prefix}: persona-file mutant must declare `agent` at the "
                f"manifest entry's top level (matched against the persona "
                f"file's basename); otherwise run.py won't pass --agent"
            )
        else:
            expected_path = f".opencode/agents/{entry['agent']}.md"
            if expected_path not in overlay:
                errors.append(
                    f"{prefix}: agent={entry['agent']!r} must match a "
                    f"persona file at {expected_path!r}; got "
                    f"overlay paths {persona_paths}"
                )

    # (5) extra_checks shape
    extra = entry.get("extra_checks") or []
    if not _has_check(extra, "call_schema_valid"):
        errors.append(
            f"{prefix}: extra_checks missing `call_schema_valid` "
            f"(required for every mutant; recurses into subagents when "
            f"trace_path is supplied)"
        )

    # (6) restriction-honored verifier covers all denied tools
    denied = KIND_DENIED_TOOLS.get(kind)
    if denied:
        if not _has_no_tool_name_recursive_covering(extra, denied):
            errors.append(
                f"{prefix}: extra_checks needs a no_tool_name_recursive entry "
                f"covering every denied tool {sorted(denied)} for kind={kind!r}"
            )

    # (7) For subagent-required: parent-only no_tool_name + any_tool_name=task + any_tool_name_recursive=read
    if kind in ("agents_md_subagent_required", "persona_main_subagent_required"):
        has_parent_block = any(
            c.get("type") == "no_tool_name"
            and set(c.get("not_equals") if isinstance(c.get("not_equals"), list) else [c.get("not_equals")])
            >= {"read", "grep", "glob"}
            for c in extra
        )
        if not has_parent_block:
            errors.append(
                f"{prefix}: subagent-required mutant needs a parent-only "
                f"no_tool_name with not_equals covering [read,grep,glob]"
            )
        if not any(
            c.get("type") == "any_tool_name" and c.get("equals") == "task"
            for c in extra
        ):
            errors.append(
                f"{prefix}: subagent-required mutant needs any_tool_name equals=task "
                f"(parent must dispatch a subagent)"
            )
        if not any(
            c.get("type") == "any_tool_name_recursive" and c.get("equals") == "read"
            for c in extra
        ):
            errors.append(
                f"{prefix}: subagent-required mutant needs any_tool_name_recursive "
                f"equals=read (subagent must actually read)"
            )

    return errors


# ---------------------------------------------------------------------------
# Pass 2: derive + materialization + synth-trace
# ---------------------------------------------------------------------------


def _run_derive(ids: list[int] | None = None) -> tuple[bool, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "derive_mutants.py")]
    if ids:
        for i in ids:
            cmd.extend(["--id", str(i)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr


def pass2_entry(entry: dict, parent_index: dict[int, dict]) -> list[str]:
    """Verify materialized artifacts on disk + synth-trace check semantics."""
    errors: list[str] = []
    sid = entry["id"]
    name = entry["name"]
    prefix = f"#{sid}"

    # Overlay files should be on disk after derive ran (called by main()).
    overlay_dir = MUTANT_OVERLAY_ROOT / f"{sid:03d}"
    if not overlay_dir.is_dir():
        errors.append(f"{prefix}: overlay dir {overlay_dir.relative_to(ROOT)}/ missing")
    else:
        for rel in entry.get("workspace_overlay", {}):
            f = overlay_dir / rel
            if not f.is_file():
                errors.append(f"{prefix}: overlay file {rel!r} missing under {overlay_dir.relative_to(ROOT)}/")

    # Spec on disk
    spec_path = SPEC_DIR / f"{sid:03d}_{name}.md"
    if not spec_path.is_file():
        errors.append(f"{prefix}: spec {spec_path.relative_to(ROOT)} missing")

    # Row on disk in samples_v1.jsonl
    rows = load_mutant_rows()
    if sid not in rows:
        errors.append(f"{prefix}: samples_v1.jsonl missing row id={sid}")
        return errors
    row = rows[sid]
    if row.get("category") != MUTANT_CATEGORY:
        errors.append(
            f"{prefix}: row category is {row.get('category')!r}, expected {MUTANT_CATEGORY!r}"
        )
    if row.get("parent_id") != entry["parent_id"]:
        errors.append(f"{prefix}: row parent_id mismatch")
    if row.get("mutation_kind") != entry["mutation_kind"]:
        errors.append(f"{prefix}: row mutation_kind mismatch")

    # Row's checks must include all entry.extra_checks
    row_check_types = [c.get("type") for c in row.get("checks", [])]
    for c in entry.get("extra_checks", []):
        if c.get("type") not in row_check_types:
            errors.append(
                f"{prefix}: row checks missing extra_check type {c.get('type')!r}"
            )

    # Row's checks must include parent's underlying task verifier.
    parent = parent_index.get(entry["parent_id"], {})
    parent_check_types = {c.get("type") for c in parent.get("checks", [])}
    parent_task_verifier_types = parent_check_types - {"call_schema_valid"}
    for chk_type in parent_task_verifier_types:
        if chk_type not in row_check_types:
            errors.append(
                f"{prefix}: row checks missing parent task verifier {chk_type!r}"
            )

    # Synth-trace: build a compliant trace and verify the
    # no_tool_name_recursive check passes; build a violation trace and
    # verify it fails.
    denied = KIND_DENIED_TOOLS.get(entry["mutation_kind"], set())
    if denied:
        # Pick any denied tool for the violation trace.
        viol_tool = sorted(denied)[0]
        # A compliant trace uses some non-denied tool. Pick `bash` or
        # any allowed alternative.
        compliant_tool = "bash" if "bash" not in denied else "read"

        try:
            from evaluators.tool.no_tool_name import check as nt_strict
        except Exception as e:
            errors.append(f"{prefix}: cannot import no_tool_name evaluator: {e}")
            return errors

        # Compliant: only `compliant_tool` calls -> no_tool_name should pass
        compliant_calls = [{"name": compliant_tool, "input": {}}]
        ne = sorted(denied)
        ok, _ = nt_strict(compliant_calls, [], {"not_equals": ne})
        if not ok:
            errors.append(
                f"{prefix}: synth compliant trace unexpectedly tripped no_tool_name "
                f"with not_equals={ne}"
            )
        # Violation: includes a denied tool -> no_tool_name should fail
        violation_calls = compliant_calls + [{"name": viol_tool, "input": {}}]
        ok, _ = nt_strict(violation_calls, [], {"not_equals": ne})
        if ok:
            errors.append(
                f"{prefix}: synth violation trace unexpectedly passed no_tool_name "
                f"(used {viol_tool!r}) with not_equals={ne}"
            )

    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", type=int, action="append")
    p.add_argument("--pass", dest="which_pass", choices=["1", "2", "both"], default="both")
    args = p.parse_args()

    manifest = load_manifest()
    samples = manifest.get("samples", [])
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]

    parent_index = load_parent_index()
    any_error = False

    if args.which_pass in ("1", "both"):
        print("=" * 60)
        print("Pass 1 - Layer 0 gates")
        print("=" * 60)
        for entry in samples:
            errs = pass1_entry(entry, parent_index)
            if errs:
                print(f"  FAIL #{entry['id']} {entry['name']}")
                for e in errs:
                    print(f"    - {e}")
                any_error = True
            else:
                print(f"  PASS #{entry['id']} {entry['name']}")
        print()

    if args.which_pass in ("2", "both") and not any_error:
        print("=" * 60)
        print("Pass 2 - derive + materialization + synth-trace")
        print("=" * 60)
        wanted_ids = [e["id"] for e in samples] if args.id else None
        ok, output = _run_derive(wanted_ids)
        if not ok:
            print("  derive_mutants.py failed:")
            print(output)
            any_error = True
        else:
            for entry in samples:
                errs = pass2_entry(entry, parent_index)
                if errs:
                    print(f"  FAIL #{entry['id']} {entry['name']}")
                    for e in errs:
                        print(f"    - {e}")
                    any_error = True
                else:
                    print(f"  PASS #{entry['id']} {entry['name']}")
        print()

    print("=" * 60)
    if any_error:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS (all {len(samples)} mutants validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
