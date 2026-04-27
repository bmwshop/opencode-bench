#!/usr/bin/env python3
"""
Audit harness for v1 code-editing samples (#51 - #60).

Ground truth is the manifest at `data/v1_editing_criteria.json`, consumed
by `scripts/regen_editing.py`. The audit does NOT hand-code assert lists;
it derives them from the same manifest and checks that the jsonl row,
the spec markdown, and the on-disk evaluator behavior are all mutually
consistent -- and that the reference edit produces the expected
pass/fail signals under multiple file mutations.

Two validation passes, both required for a sample to be considered correct:

Pass 1 - in-process
    * Re-run the authoring gates from scripts.regen_editing (anchor
      uniqueness, AST presence, assert classification, D in [2, 4],
      determinism sub-gates, prompt does not leak file path).
    * Derive the patched file from `reference_edit` and materialize
      it in a tempdir.
    * Invoke `evaluators.content.exec_assert.check` directly against
      the patched file (positive expected to PASS).
    * Re-invoke against the baseline (unedited) file (expected to FAIL
      on a new-behavior assert).
    * Synthesize a 'regression-only' subset (drop every assert with
      kind=='new_behavior') and verify it PASSES against the baseline
      file -- this guards against regression asserts that accidentally
      depend on post-edit behavior.
    * Synthesize a syntax-error variant by appending a stray '(' to
      the patched file and verify exec_assert FAILS (expected reason:
      SyntaxError).
    * Verify that the sample's assert list covers >=3 distinct
      non-'none' misstep classes.
    * Cross-check that the samples_v1.jsonl row embeds the same
      functions / constants / imports / asserts the manifest declares.

Pass 2 - end-to-end through eval.py
    * Synthesize a minimal opencode trace whose `edit` tool call
      supplies the canonical `filePath` / `oldString` / `newString`
      field names. Materialize the per-sample workspace under a fake
      runs/ tree with the edit already applied on disk.
    * Invoke `eval.evaluate(sample, run_dir)`. Both declared checks
      (exec_assert, call_schema_valid) must return pass.
    * Construct a malformed-args trace (wrong field name: `path`
      instead of `filePath`) and verify call_schema_valid fails.
    * Between the positive and negative trace variants, call
      `_collect_recursive_tools.cache_clear()` because the trace path
      is memoized on content.

Usage
    python3 scripts/audit_editing.py             # all v1 editing samples
    python3 scripts/audit_editing.py --id 51     # one sample
    python3 scripts/audit_editing.py --pass 1    # only pass 1
    python3 scripts/audit_editing.py --pass 2    # only pass 2
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import evaluators  # noqa: E402
from common import SAMPLES_V1  # noqa: E402
from scripts.regen_editing import (  # noqa: E402
    authoring_gates,
    build_prompt,
    build_row,
    discovery_files,
    load_manifest,
    primary_function,
    repo_for,
    repo_root,
    targets_of,
)

# Editing samples currently span ids 51..60 (requests) plus the planned 61..80
# (httpx) expansion. Reserve 81..90 for future additions; treat the full range
# 51..90 as the editing slice for audit purposes.
EDIT_IDS = set(range(51, 91))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_editing_samples(ids: list[int] | None = None) -> list[dict[str, Any]]:
    out = []
    if not SAMPLES_V1.exists():
        return out
    with open(SAMPLES_V1) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            s = json.loads(line)
            if s.get("id") not in EDIT_IDS:
                continue
            if ids and s["id"] not in ids:
                continue
            out.append(s)
    return out


def load_ground_truth(ids: list[int] | None = None) -> dict[int, dict[str, Any]]:
    manifest = load_manifest()
    out: dict[int, dict[str, Any]] = {}
    for entry in manifest.get("samples", []):
        sid = entry["id"]
        if ids and sid not in ids:
            continue
        out[sid] = entry
    return out


def _strip_assert_fields(a: dict) -> dict:
    return {k: v for k, v in a.items() if k in ("expr", "setup")}


def _chk_from_entry(entry: dict, project_dir: Path) -> dict:
    targets = targets_of(entry)
    asserts = [_strip_assert_fields(a) for a in entry["asserts"]]
    if len(targets) == 1:
        t = targets[0]
        return {
            "type": "exec_assert",
            "_project_dir": str(project_dir),
            "path": t["path"],
            "functions": list(t["functions"]),
            "constants": list(t["constants"]),
            "imports": list(t["imports"]),
            "asserts": asserts,
            "timeout": 15,
        }
    return {
        "type": "exec_assert",
        "_project_dir": str(project_dir),
        "targets": [
            {
                "path": t["path"],
                "functions": list(t["functions"]),
                "constants": list(t["constants"]),
                "imports": list(t["imports"]),
            }
            for t in targets
        ],
        "asserts": asserts,
        "timeout": 20,
    }


def _regression_only_chk(entry: dict, project_dir: Path) -> dict:
    """Regression-only check.

    Multi-file samples may declare synthetic-helper targets (`is_new: true`)
    whose function bodies only exist after the reference edit; against the
    baseline workspace those targets won't load, so they are stripped here.
    Regression asserts are only allowed to reference symbols on
    non-`is_new` targets.
    """
    chk = _chk_from_entry(entry, project_dir)
    chk["asserts"] = [
        _strip_assert_fields(a) for a in entry["asserts"] if a.get("kind") == "regression"
    ]
    if "targets" in chk:
        kept = []
        for t, mt in zip(chk["targets"], targets_of(entry)):
            if mt.get("is_new"):
                continue
            kept.append(t)
        if len(kept) == 1:
            t = kept[0]
            return {
                "type": "exec_assert",
                "_project_dir": chk["_project_dir"],
                "path": t["path"],
                "functions": list(t["functions"]),
                "constants": list(t["constants"]),
                "imports": list(t["imports"]),
                "asserts": chk["asserts"],
                "timeout": chk.get("timeout", 15),
            }
        chk["targets"] = kept
    return chk


def _apply_edit(baseline_src: str, ref_edit: dict) -> str:
    return baseline_src.replace(ref_edit["oldString"], ref_edit["newString"], 1)


def _materialize_workspace(td: Path, entry: dict, mode: str) -> None:
    """Copy each target's baseline file into td and (optionally) apply the
    reference edit. `mode` is 'baseline' or 'patched'.
    """
    root = repo_root(repo_for(entry))
    for t in targets_of(entry):
        src = (root / t["path"]).read_text()
        body = _apply_edit(src, t["reference_edit"]) if mode == "patched" else src
        out = td / t["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)


# ---------------------------------------------------------------------------
# Pass 1 - in-process
# ---------------------------------------------------------------------------


def pass1_sample(
    entry: dict,
    row: dict,
    exec_assert_fn,
) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    # (a) Re-run authoring gates (D already computed in regen; redo for isolation).
    try:
        slug = repo_for(entry)
        per_probe = []
        union: set[str] = set()
        for pat in entry["discovery_probes"]:
            hits = discovery_files([pat], slug)
            per_probe.append((pat, hits))
            union.update(hits)
        discovery = {"per_probe": per_probe, "union": sorted(union)}
        prompt = build_prompt(entry)
        gate_errs = authoring_gates(entry, prompt, discovery)
        errors.extend(gate_errs)
    except Exception as e:
        errors.append(f"{prefix}: authoring-gate run crashed: {type(e).__name__}: {e}")
        return errors

    # (b) Row consistency with manifest.
    exec_chk = next((c for c in row.get("checks", []) if c["type"] == "exec_assert"), None)
    if exec_chk is None:
        errors.append(f"{prefix}: row has no exec_assert check")
        return errors

    targets = targets_of(entry)
    if len(targets) == 1:
        t = targets[0]
        if exec_chk.get("path") != t["path"]:
            errors.append(
                f"{prefix}: row.exec_assert.path {exec_chk.get('path')!r} != manifest target path {t['path']!r}"
            )
        if list(exec_chk.get("functions", [])) != list(t["functions"]):
            errors.append(f"{prefix}: row.functions != manifest.functions")
        if list(exec_chk.get("constants", []) or []) != list(t["constants"]):
            errors.append(f"{prefix}: row.constants != manifest.constants")
        if list(exec_chk.get("imports", []) or []) != list(t["imports"]):
            errors.append(f"{prefix}: row.imports != manifest.imports")
    else:
        row_targets = exec_chk.get("targets") or []
        if len(row_targets) != len(targets):
            errors.append(
                f"{prefix}: row exec_assert has {len(row_targets)} targets; "
                f"manifest declares {len(targets)}"
            )
        for ti, (rt, mt) in enumerate(zip(row_targets, targets)):
            for k in ("path", "functions", "constants", "imports"):
                row_v = rt.get(k) or [] if k != "path" else rt.get(k)
                man_v = mt[k]
                if row_v != man_v:
                    errors.append(
                        f"{prefix}: row.targets[{ti}].{k}={row_v!r} != manifest {man_v!r}"
                    )
    row_asserts = exec_chk.get("asserts", [])
    want_asserts = [_strip_assert_fields(a) for a in entry["asserts"]]
    if row_asserts != want_asserts:
        errors.append(
            f"{prefix}: row asserts != manifest asserts (len {len(row_asserts)} vs {len(want_asserts)})"
        )

    # (c) >=3 distinct non-'none' misstep classes.
    missteps = {a["misstep"] for a in entry["asserts"] if a.get("misstep") not in (None, "none")}
    if len(missteps) < 3:
        errors.append(f"{prefix}: only {len(missteps)} distinct misstep classes ({sorted(missteps)}); need >=3")

    # (d) Reference edit must actually change something for every target.
    root = repo_root(repo_for(entry))
    for t in targets:
        baseline = (root / t["path"]).read_text()
        patched = _apply_edit(baseline, t["reference_edit"])
        if patched == baseline:
            errors.append(f"{prefix}: reference edit on {t['path']} is a no-op")
            return errors

    # (e) Materialize variants and run exec_assert.
    with tempfile.TemporaryDirectory(prefix="audit_edit_p1_") as td:
        td_path = Path(td)
        chk = _chk_from_entry(entry, td_path)

        # (e.i) positive must pass (all targets patched).
        _materialize_workspace(td_path, entry, "patched")
        ok, reason = exec_assert_fn([], [], chk)
        if not ok:
            errors.append(f"{prefix}: positive variant failed: {reason}")

        # (e.ii) baseline must fail full assert list (no targets patched).
        _materialize_workspace(td_path, entry, "baseline")
        ok, reason = exec_assert_fn([], [], chk)
        if ok:
            errors.append(f"{prefix}: baseline unexpectedly passed full assert list")

        # (e.iii) regression-only must pass against baseline.
        reg_chk = _regression_only_chk(entry, td_path)
        if reg_chk["asserts"]:
            ok, reason = exec_assert_fn([], [], reg_chk)
            if not ok:
                errors.append(
                    f"{prefix}: regression-only subset failed against baseline: {reason}"
                )

        # (e.iv) hard-tier multi-file: applying just one half of the patch
        # must FAIL (proves the cross-file edit is genuinely required).
        if len(targets) > 1:
            for ti, t in enumerate(targets):
                # patched: only this target; baseline: all the others.
                _materialize_workspace(td_path, entry, "baseline")
                src_path = td_path / t["path"]
                src_path.write_text(_apply_edit((root / t["path"]).read_text(),
                                                t["reference_edit"]))
                ok, _ = exec_assert_fn([], [], chk)
                if ok:
                    errors.append(
                        f"{prefix}: applying only target #{ti} ({t['path']}) passed; "
                        f"the cross-file edit is not actually required"
                    )

        # (e.v) syntax-error variant must fail (corrupt the first patched target).
        _materialize_workspace(td_path, entry, "patched")
        first_target = targets[0]
        bad_path = td_path / first_target["path"]
        bad_path.write_text(bad_path.read_text() + "\n\n(\n")
        ok, _ = exec_assert_fn([], [], chk)
        if ok:
            errors.append(f"{prefix}: syntax-error variant unexpectedly passed")

    return errors


# ---------------------------------------------------------------------------
# Pass 2 - end-to-end through eval.py
# ---------------------------------------------------------------------------


def _synthesize_edit_trace(
    trace_path: Path,
    correct: bool,
    entry: dict,
) -> None:
    """Write a minimal opencode trace with one `edit` tool call per target.

    If correct=True the tool_use(s) use canonical schema fields
    (`filePath`, `oldString`, `newString`). If correct=False the FIRST
    edit call uses the wrong key `path` instead of `filePath` so
    call_schema_valid will reject the call.
    """
    targets = targets_of(entry)
    events: list[dict] = [{"type": "step_start"}]
    events.append({
        "type": "tool_use",
        "part": {
            "tool": "grep",
            "state": {"input": {"pattern": primary_function(entry)}, "output": ""},
        },
    })
    for t in targets:
        events.append({
            "type": "tool_use",
            "part": {
                "tool": "read",
                "state": {"input": {"filePath": t["path"]}, "output": ""},
            },
        })
    for i, t in enumerate(targets):
        if i == 0 and not correct:
            tool_input: dict[str, Any] = {
                "path": t["path"],
                "oldString": t["reference_edit"]["oldString"],
                "newString": t["reference_edit"]["newString"],
            }
        else:
            tool_input = {
                "filePath": t["path"],
                "oldString": t["reference_edit"]["oldString"],
                "newString": t["reference_edit"]["newString"],
            }
        events.append({
            "type": "tool_use",
            "part": {
                "tool": "edit",
                "state": {"input": tool_input, "output": "ok"},
            },
        })
    files_summary = ", ".join(t["path"] for t in targets)
    events.append({"type": "text", "part": {"text": f"Edited {files_summary}"}})
    trace_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def pass2_sample(entry: dict, sample: dict) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    import eval as eval_mod
    from common import run_project_name, trace_name
    from evaluators._recursive import _collect_recursive_tools

    eval_mod.load_evaluators()

    with tempfile.TemporaryDirectory(prefix="audit_edit_p2_") as td:
        run_dir = Path(td)
        proj_dir = run_dir / "projects" / run_project_name(sample)
        shutil.copytree(repo_root(repo_for(entry)), proj_dir)
        # Apply edit(s) on disk so exec_assert sees the patched file(s).
        for t in targets_of(entry):
            tgt = proj_dir / t["path"]
            baseline = tgt.read_text()
            tgt.write_text(_apply_edit(baseline, t["reference_edit"]))

        trace_file = run_dir / f"{trace_name(sample)}.jsonl"

        # Positive: canonical args; both checks must pass.
        _synthesize_edit_trace(trace_file, correct=True, entry=entry)
        result = eval_mod.evaluate(sample, run_dir)
        if not result.ok:
            errors.append(
                f"{prefix}: positive end-to-end failed. "
                f"passed={result.passed} failed={result.failed}"
            )

        # Negative: malformed args; call_schema_valid must fail.
        _collect_recursive_tools.cache_clear()
        _synthesize_edit_trace(trace_file, correct=False, entry=entry)
        result_bad = eval_mod.evaluate(sample, run_dir)
        if result_bad.ok:
            errors.append(
                f"{prefix}: malformed-args negative unexpectedly passed. "
                f"passed={result_bad.passed}"
            )
        else:
            blob = " | ".join(result_bad.failed)
            if "call_schema_valid" not in blob and "edit" not in blob:
                errors.append(
                    f"{prefix}: malformed-args negative failed for unexpected reason: "
                    f"{result_bad.failed}"
                )

    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", type=int, action="append")
    p.add_argument("--pass", dest="which_pass", choices=["1", "2", "both"], default="both")
    args = p.parse_args()

    samples = load_editing_samples(args.id)
    if not samples:
        print("No v1 editing samples found in samples_v1.jsonl.")
        return 1

    gt = load_ground_truth(args.id)
    rows_by_id = {s["id"]: s for s in samples}

    # Ensure evaluators are registered (exec_assert, call_schema_valid, ...).
    import eval as eval_mod
    eval_mod.load_evaluators()
    exec_assert_fn = evaluators.get("exec_assert")
    if exec_assert_fn is None:
        print("ERROR: exec_assert evaluator not registered", file=sys.stderr)
        return 2

    all_errors: list[str] = []

    if args.which_pass in ("1", "both"):
        print("=" * 60)
        print("Pass 1 - in-process validation")
        print("=" * 60)
        for sid in sorted(gt):
            entry = gt[sid]
            row = rows_by_id.get(sid)
            if row is None:
                err = f"#{sid}: manifest entry has no row in samples_v1.jsonl"
                print(f"  FAIL {err}")
                all_errors.append(err)
                continue
            errs = pass1_sample(entry, row, exec_assert_fn)
            label = f"#{sid} {entry['name']}"
            if errs:
                print(f"  FAIL {label}")
                for e in errs:
                    print(f"    - {e}")
                all_errors.extend(errs)
            else:
                print(f"  PASS {label}")

    if args.which_pass in ("2", "both"):
        print()
        print("=" * 60)
        print("Pass 2 - end-to-end through eval.py")
        print("=" * 60)
        for sid in sorted(gt):
            entry = gt[sid]
            row = rows_by_id.get(sid)
            if row is None:
                continue
            errs = pass2_sample(entry, row)
            label = f"#{sid} {entry['name']}"
            if errs:
                print(f"  FAIL {label}")
                for e in errs:
                    print(f"    - {e}")
                all_errors.extend(errs)
            else:
                print(f"  PASS {label}")

    print()
    print("=" * 60)
    if all_errors:
        print(f"RESULT: FAIL ({len(all_errors)} error{'s' if len(all_errors) != 1 else ''})")
        return 1
    print(f"RESULT: PASS (all {len(samples)} samples validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
