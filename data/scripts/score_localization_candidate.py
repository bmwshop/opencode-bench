#!/usr/bin/env python3
"""
Score a candidate localization-sample stub against the oracle.

Given a JSON file shaped like an entry in `data/v1_localization_criteria.json`
(but without `difficulty` and without a finalized `unique_trait`), this
script runs the oracle end-to-end, cross-checks against `rg`, and reports:

  * gold entry count, file fan-out, and the derived gold listing;
  * an auto-estimated `difficulty` tier;
  * a structural-signature uniqueness check against existing manifest entries
    (flags any existing sample whose non-`unique_trait` signature tuple is
    identical — the designer can still keep the candidate by supplying a
    distinct `unique_trait`).

Expected candidate JSON
-----------------------

T1::

    {
      "template": "T1",
      "scope": ["src/requests/cookies.py", "src/requests/sessions.py"],
      "anchor": {"file": "src/requests/cookies.py",
                 "name": "merge_cookies",
                 "module_level": true}
    }

T2::

    {
      "template": "T2",
      "scope": "src/requests/",
      "targets": ["iter_content", "iter_lines", "raise_for_status", "close"]
    }

Exit code is 0 when the candidate is viable (oracle runs, entries count is
within bounds, cross-check passes), nonzero otherwise. Always prints JSON
diagnostics to stdout.
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
    FuncAnalysis,
    analyze_scope,
    anchor_and_callers,
    callers_of_set,
    cross_check_rg_calls,
    cross_check_rg_calls_t2,
)

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_localization_criteria.json"


# Keep these in sync with the proposer.
MIN_ENTRIES = 2
MAX_ENTRIES = 14


def _existing_entries() -> list[dict[str, Any]]:
    return json.loads(MANIFEST_PATH.read_text()).get("samples", [])


def _predict_difficulty(n_entries: int, n_files: int, *, has_nested_def: bool, has_name_collision: bool, has_decorator: bool, has_async: bool) -> str:
    traps = sum((has_nested_def, has_name_collision, has_decorator, has_async))
    if n_entries <= 3 and n_files <= 2 and traps == 0:
        return "easy"
    if n_entries >= 7 or n_files >= 4 or traps >= 1:
        return "hard"
    return "medium"


def _sig_tuple(sig: dict[str, Any]) -> tuple:
    """Canonical sig tuple (template, scope_kind, {anchor|target}_kind, entries, files)."""
    return (
        sig.get("template"),
        sig.get("scope_kind"),
        sig.get("anchor_kind") if sig.get("template") == "T1" else sig.get("target_kind"),
        sig.get("answer_entries"),
        sig.get("answer_files"),
    )


def _uniqueness_report(candidate_sig: dict[str, Any]) -> list[dict[str, Any]]:
    cand_tuple = _sig_tuple(candidate_sig)
    hits: list[dict[str, Any]] = []
    for e in _existing_entries():
        sig = e.get("structural_signature", {})
        if _sig_tuple(sig) == cand_tuple:
            hits.append({
                "id": e.get("id"),
                "difficulty": e.get("difficulty"),
                "structural_signature": sig,
            })
    return hits


def _score_t1(cand: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    a = cand["anchor"]
    scope = cand["scope"]
    require_module_level = bool(a.get("module_level", True))
    allow_dec = bool(cand.get("allow_decorators", False))

    try:
        result = anchor_and_callers(
            anchor_file=a["file"],
            anchor_name=a["name"],
            scope=scope,
            require_module_level_anchor=require_module_level,
            allow_decorators=allow_dec,
        )
    except Exception as e:
        return 2, {"ok": False, "stage": "derive", "error": repr(e)}

    try:
        cross_check_rg_calls(result.scope_files, a["name"], result.call_sites)
    except Exception as e:
        return 3, {"ok": False, "stage": "rg_cross_check", "error": repr(e)}

    n_entries = len(result.entries)
    n_files = len({e.split("::", 1)[0] for e in result.entries})
    if not (MIN_ENTRIES <= n_entries <= MAX_ENTRIES):
        return 4, {
            "ok": False,
            "stage": "entry_count",
            "error": f"entries={n_entries} outside [{MIN_ENTRIES},{MAX_ENTRIES}]",
            "entries": result.entries,
        }

    # Trait signals drawn from the scope.
    analyses = analyze_scope(scope)
    by_entry: dict[str, FuncAnalysis] = {a.info.entry: a for a in analyses}
    anchor_a = by_entry.get(result.anchor.entry)
    callers_a = [by_entry[c.entry] for c in result.callers if c.entry in by_entry]
    has_nested = bool(anchor_a and anchor_a.has_nested_def) or any(
        c.has_nested_def for c in callers_a
    )
    has_async = bool(anchor_a and anchor_a.is_async) or any(
        c.is_async for c in callers_a
    )
    has_decorator = bool(anchor_a and anchor_a.has_decorator)

    difficulty = _predict_difficulty(
        n_entries, n_files,
        has_nested_def=has_nested,
        has_name_collision=False,
        has_decorator=has_decorator,
        has_async=has_async,
    )

    sig = {
        "template": "T1",
        "scope_kind": _scope_kind(n_files),
        "anchor_kind": anchor_a.anchor_kind if anchor_a else "unknown",
        "answer_entries": n_entries,
        "answer_files": n_files,
        "unique_trait": cand.get("unique_trait_hint", "TBD"),
    }

    diag = {
        "ok": True,
        "template": "T1",
        "anchor_entry": result.anchor.entry,
        "gold_entries": result.entries,
        "entries_count": n_entries,
        "files_count": n_files,
        "predicted_difficulty": difficulty,
        "structural_signature": sig,
        "signature_collisions": _uniqueness_report(sig),
        "traits": {
            "has_nested_def": has_nested,
            "has_async": has_async,
            "has_decorator": has_decorator,
        },
        "call_sites": result.call_sites,
    }
    return 0, diag


def _score_t2(cand: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    scope = cand["scope"]
    targets = cand["targets"]

    try:
        result = callers_of_set(targets=targets, scope=scope)
    except Exception as e:
        return 2, {"ok": False, "stage": "derive", "error": repr(e)}

    try:
        cross_check_rg_calls_t2(result)
    except Exception as e:
        return 3, {"ok": False, "stage": "rg_cross_check", "error": repr(e)}

    n_entries = len(result.entries)
    n_files = len({e.split("::", 1)[0] for e in result.entries})
    if not (MIN_ENTRIES <= n_entries <= MAX_ENTRIES):
        return 4, {
            "ok": False,
            "stage": "entry_count",
            "error": f"entries={n_entries} outside [{MIN_ENTRIES},{MAX_ENTRIES}]",
            "entries": result.entries,
        }

    analyses = analyze_scope(scope)
    by_entry: dict[str, FuncAnalysis] = {a.info.entry: a for a in analyses}
    names_in_scope = {a.info.name for a in analyses}
    has_nested = any(
        by_entry[c.entry].has_nested_def
        for c in result.callers
        if c.entry in by_entry
    )
    # name_collision: a non-target function definition shares its bare name
    # with one of the targets.
    has_collision = any(
        t in names_in_scope and any(
            a.info.name == t and a.info.qualname != t  # not module-level target itself
            for a in analyses
        )
        for t in targets
    )

    difficulty = _predict_difficulty(
        n_entries, n_files,
        has_nested_def=has_nested,
        has_name_collision=has_collision,
        has_decorator=False,
        has_async=False,
    )

    sig = {
        "template": "T2",
        "scope_kind": _scope_kind(n_files, t2=True),
        "target_kind": cand.get("target_kind", "TBD"),
        "answer_entries": n_entries,
        "answer_files": n_files,
        "unique_trait": cand.get("unique_trait_hint", "TBD"),
    }

    diag = {
        "ok": True,
        "template": "T2",
        "targets": result.targets,
        "gold_entries": result.entries,
        "entries_count": n_entries,
        "files_count": n_files,
        "predicted_difficulty": difficulty,
        "structural_signature": sig,
        "signature_collisions": _uniqueness_report(sig),
        "traits": {
            "has_nested_def": has_nested,
            "has_name_collision": has_collision,
        },
        "call_sites": result.call_sites,
        "call_sites_by_target": result.__dict__.get("call_sites_by_target", {}),
    }
    return 0, diag


def _scope_kind(n_files: int, *, t2: bool = False) -> str:
    if t2:
        return "any_file" if n_files > 4 else f"{_num_word(n_files)}_files"
    return f"{_num_word(n_files)}_files" if n_files > 1 else "single_file"


def _num_word(n: int) -> str:
    return {1: "single", 2: "two", 3: "three", 4: "four"}.get(n, f"{n}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True,
                   help="path to candidate JSON (shape described in module docstring)")
    p.add_argument("--output", type=Path, help="write diagnostics JSON here instead of stdout")
    args = p.parse_args()

    cand = json.loads(args.input.read_text())
    tmpl = cand.get("template")
    if tmpl == "T1":
        rc, diag = _score_t1(cand)
    elif tmpl == "T2":
        rc, diag = _score_t2(cand)
    else:
        rc = 2
        diag = {"ok": False, "stage": "parse", "error": f"unknown template {tmpl!r}"}

    text = json.dumps(diag, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
        print(f"wrote {args.output} (rc={rc})")
    else:
        print(text)
    return rc


if __name__ == "__main__":
    sys.exit(main())
