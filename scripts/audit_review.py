#!/usr/bin/env python3
"""
Audit harness for v1 paper-faithful code-review samples (#91-#100).

Pass 1 - label oracle (mechanical, in-process)
    For each sample, resolves the (source_manifest, source_id, variant)
    cross-reference to a list of patches, applies them on top of the
    pinned baseline in a temp workspace, runs `evaluators.content.exec_assert`
    against the source's truth table, and verifies the outcome matches the
    declared `label`:

        label="YES" iff exec_assert returns ok==True
        label="NO"  iff exec_assert returns ok==False (>=1 assert failed)

    Mismatch means the manifest is wrong (label disagrees with the gold
    truth table). The audit fails loudly.

Pass 2 - end-to-end through eval.py
    Synthesizes a minimal plan-mode trace: 1-2 read calls + a final text
    response containing `<judgment>{LABEL}</judgment>` + `<review>...</review>`.
    Runs `eval.evaluate(sample, run_dir)` and verifies all 4 checks pass.
    Then runs three negative variants (wrong judgment, missing review tags,
    edit/bash call), each of which must fail the appropriate check.

Usage
-----
    python3 scripts/audit_review.py            # all samples, both passes
    python3 scripts/audit_review.py --id 91    # one sample
    python3 scripts/audit_review.py --pass 1
    python3 scripts/audit_review.py --pass 2
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
from common import SAMPLES_V1, PROJECTS  # noqa: E402
from scripts.regen_review import (  # noqa: E402
    REVIEW_IDS,
    authoring_gates,
    build_prompt,
    build_row,
    load_manifest,
    load_source_entry,
    resolve_patches,
)

V1_REQUESTS_ROOT = PROJECTS / "v1" / "requests"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_review_samples(ids: list[int] | None = None) -> list[dict[str, Any]]:
    out = []
    if not SAMPLES_V1.exists():
        return out
    with open(SAMPLES_V1) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            s = json.loads(line)
            if s.get("id") not in REVIEW_IDS:
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
        if sid not in REVIEW_IDS:
            continue
        if ids and sid not in ids:
            continue
        out[sid] = entry
    return out


# ---------------------------------------------------------------------------
# Pass 1 helpers: label oracle via exec_assert against source's asserts
# ---------------------------------------------------------------------------


def _materialize_patched_workspace(td: Path, source: dict, patches: list[dict]) -> None:
    """Copy each patched-target baseline into td and apply the patch.

    Files NOT in `patches` are not copied (exec_assert only reads the
    paths declared in its config; we keep td minimal).
    """
    for p in patches:
        baseline = (V1_REQUESTS_ROOT / p["path"]).read_text()
        n = baseline.count(p["oldString"])
        if n != 1:
            raise ValueError(
                f"patch {p['path']!r}: oldString occurs {n} times (expected 1)"
            )
        body = baseline.replace(p["oldString"], p["newString"], 1)
        out = td / p["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)


def _strip_assert_fields(a: dict) -> dict:
    return {k: v for k, v in a.items() if k in ("expr", "setup")}


def _exec_assert_chk_for_source(source: dict, td_path: Path) -> dict:
    """Build an exec_assert check config from the SOURCE manifest entry.

    Mirrors the logic in scripts/audit_editing.py::_chk_from_entry.
    """
    asserts = [_strip_assert_fields(a) for a in source["asserts"]]
    if source.get("targets"):
        return {
            "type": "exec_assert",
            "_project_dir": str(td_path),
            "targets": [
                {
                    "path": t["path"],
                    "functions": list(t.get("functions") or []),
                    "constants": list(t.get("constants") or []),
                    "imports": list(t.get("imports") or []),
                }
                for t in source["targets"]
            ],
            "asserts": asserts,
            "timeout": 20,
        }
    return {
        "type": "exec_assert",
        "_project_dir": str(td_path),
        "path": source["file"],
        "functions": list(source.get("functions") or []),
        "constants": list(source.get("constants") or []),
        "imports": list(source.get("imports") or []),
        "asserts": asserts,
        "timeout": 15,
    }


def label_oracle(entry: dict, source: dict, exec_assert_fn) -> tuple[str, str]:
    """Run exec_assert against the source's truth table on the variant-patched workspace.

    Returns (computed_label, reason). computed_label is "YES" or "NO".
    """
    patches = resolve_patches(source, entry["variant"])
    # Multi-file source: we need ALL targets present in the workspace, even
    # those not modified by the variant patch (so exec_assert can load them).
    needed_paths: set[str] = set()
    if source.get("targets"):
        needed_paths = {t["path"] for t in source["targets"]}
    else:
        needed_paths = {source["file"]}
    patched_paths = {p["path"] for p in patches}

    with tempfile.TemporaryDirectory(prefix="audit_review_p1_") as td:
        td_path = Path(td)
        # First: copy every needed path as baseline.
        for path_str in needed_paths:
            baseline = (V1_REQUESTS_ROOT / path_str).read_text()
            out = td_path / path_str
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(baseline)
        # Then: apply patches (overwrite the baseline copies for those paths).
        _materialize_patched_workspace(td_path, source, patches)
        # Sanity: every patched path must be in needed_paths.
        bad = patched_paths - needed_paths
        if bad:
            return ("?", f"patched paths {bad} not in source's target paths {needed_paths}")
        # Run exec_assert with the source's full truth table.
        chk = _exec_assert_chk_for_source(source, td_path)
        ok, reason = exec_assert_fn([], [], chk)
        return ("YES" if ok else "NO", reason or "")


# ---------------------------------------------------------------------------
# Pass 1
# ---------------------------------------------------------------------------


def pass1_sample(entry: dict, row: dict, exec_assert_fn) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    # (a) re-run authoring gates.
    try:
        source = load_source_entry(entry["source_manifest"], entry["source_id"])
    except (FileNotFoundError, KeyError) as e:
        errors.append(f"{prefix}: source resolution: {e}")
        return errors
    errs = authoring_gates(entry, source)
    errors.extend(errs)

    # (b) row consistency.
    expect_label = entry["label"]
    judgment_check_pat = rf"<judgment>\s*{expect_label}\s*</judgment>"
    chks = row.get("checks", [])
    types = [c.get("type") for c in chks]
    if "no_tool_name" not in types:
        errors.append(f"{prefix}: row missing no_tool_name check")
    if "call_schema_valid" not in types:
        errors.append(f"{prefix}: row missing call_schema_valid check")
    text_chks = [c for c in chks if c.get("type") == "text_contains"]
    if not any(c.get("pattern") == judgment_check_pat for c in text_chks):
        errors.append(
            f"{prefix}: row missing the judgment-gate text_contains "
            f"(expected pattern {judgment_check_pat!r})"
        )
    review_pat = r"<review>[\s\S]*?</review>"
    if not any(c.get("pattern") == review_pat for c in text_chks):
        errors.append(f"{prefix}: row missing the <review> structured-output gate")
    if row.get("agent") != "plan":
        errors.append(f"{prefix}: row.agent = {row.get('agent')!r}, expected 'plan'")
    if row.get("surface") != "modes":
        errors.append(f"{prefix}: row.surface = {row.get('surface')!r}, expected 'modes'")
    if row.get("category") != "code_review":
        errors.append(
            f"{prefix}: row.category = {row.get('category')!r}, expected 'code_review'"
        )

    if errors:
        return errors

    # (c) label oracle: run exec_assert against the source's truth table on the
    # variant-patched workspace. Outcome must match declared label.
    try:
        computed, reason = label_oracle(entry, source, exec_assert_fn)
    except (ValueError, IndexError, KeyError) as e:
        errors.append(f"{prefix}: label oracle crashed: {e}")
        return errors
    if computed != expect_label:
        errors.append(
            f"{prefix}: label oracle disagrees with manifest. "
            f"manifest declares label={expect_label!r}; exec_assert says {computed!r}. "
            f"reason: {reason}"
        )

    return errors


# ---------------------------------------------------------------------------
# Pass 2 helpers: synthesize plan-mode traces
# ---------------------------------------------------------------------------


def _synthesize_plan_trace(
    trace_path: Path,
    *,
    judgment: str,
    include_review: bool,
    include_edit_call: bool,
    include_bad_read_args: bool,
    source: dict,
) -> None:
    """Write a minimal plan-mode opencode trace."""
    events: list[dict] = [{"type": "step_start"}]
    # 1 read call against the primary source path (paths exist in workspace).
    primary_path = (
        source["targets"][0]["path"] if source.get("targets") else source["file"]
    )
    if include_bad_read_args:
        # malformed: opencode read uses "filePath", supplying "path" fails the schema.
        events.append({
            "type": "tool_use",
            "part": {
                "tool": "read",
                "state": {"input": {"path": primary_path}, "output": ""},
            },
        })
    else:
        events.append({
            "type": "tool_use",
            "part": {
                "tool": "read",
                "state": {"input": {"filePath": primary_path}, "output": ""},
            },
        })

    if include_edit_call:
        # plan-mode-violating edit call.
        events.append({
            "type": "tool_use",
            "part": {
                "tool": "edit",
                "state": {
                    "input": {
                        "filePath": primary_path,
                        "oldString": "x",
                        "newString": "y",
                    },
                    "output": "",
                },
            },
        })

    review_block = (
        "<review>\nThis PR addresses the issue by adding the necessary guard.\n</review>\n\n"
        if include_review
        else ""
    )
    text = (
        f"After reviewing the diff against the issue:\n\n"
        f"{review_block}"
        f"<judgment>\n{judgment}\n</judgment>"
    )
    events.append({"type": "text", "part": {"text": text}})
    trace_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def pass2_sample(entry: dict, sample: dict) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    import eval as eval_mod
    from common import run_project_name, trace_name
    from evaluators._recursive import _collect_recursive_tools

    eval_mod.load_evaluators()

    try:
        source = load_source_entry(entry["source_manifest"], entry["source_id"])
    except (FileNotFoundError, KeyError) as e:
        errors.append(f"{prefix}: source resolution: {e}")
        return errors

    label = entry["label"]
    wrong_label = "NO" if label == "YES" else "YES"

    with tempfile.TemporaryDirectory(prefix="audit_review_p2_") as td:
        run_dir = Path(td)
        proj_dir = run_dir / "projects" / run_project_name(sample)
        # Plan-mode workspace: we DO NOT apply the patch; the agent only reads
        # the baseline. The diff is in the prompt, not on disk.
        shutil.copytree(V1_REQUESTS_ROOT, proj_dir)
        trace_file = run_dir / f"{trace_name(sample)}.jsonl"

        # Positive: correct judgment + review block + clean read args, no edit.
        _synthesize_plan_trace(
            trace_file,
            judgment=label,
            include_review=True,
            include_edit_call=False,
            include_bad_read_args=False,
            source=source,
        )
        result = eval_mod.evaluate(sample, run_dir)
        if not result.ok:
            errors.append(
                f"{prefix}: positive end-to-end failed. "
                f"passed={result.passed} failed={result.failed}"
            )

        # Negative 1: wrong judgment - text_contains judgment-gate must fail.
        _collect_recursive_tools.cache_clear()
        _synthesize_plan_trace(
            trace_file,
            judgment=wrong_label,
            include_review=True,
            include_edit_call=False,
            include_bad_read_args=False,
            source=source,
        )
        bad = eval_mod.evaluate(sample, run_dir)
        if bad.ok:
            errors.append(
                f"{prefix}: wrong-judgment negative unexpectedly passed."
            )
        else:
            blob = " | ".join(bad.failed)
            if "judgment" not in blob:
                errors.append(
                    f"{prefix}: wrong-judgment negative failed for unexpected reason: {bad.failed}"
                )

        # Negative 2: missing <review> tags - structured-output gate must fail.
        _collect_recursive_tools.cache_clear()
        _synthesize_plan_trace(
            trace_file,
            judgment=label,
            include_review=False,
            include_edit_call=False,
            include_bad_read_args=False,
            source=source,
        )
        bad = eval_mod.evaluate(sample, run_dir)
        if bad.ok:
            errors.append(
                f"{prefix}: missing-review-tags negative unexpectedly passed."
            )
        else:
            blob = " | ".join(bad.failed)
            if "review" not in blob:
                errors.append(
                    f"{prefix}: missing-review-tags negative failed for unexpected reason: {bad.failed}"
                )

        # Negative 3: edit call - plan-mode no_tool_name gate must fail.
        _collect_recursive_tools.cache_clear()
        _synthesize_plan_trace(
            trace_file,
            judgment=label,
            include_review=True,
            include_edit_call=True,
            include_bad_read_args=False,
            source=source,
        )
        bad = eval_mod.evaluate(sample, run_dir)
        if bad.ok:
            errors.append(
                f"{prefix}: edit-call negative unexpectedly passed."
            )
        else:
            blob = " | ".join(bad.failed)
            if "edit" not in blob:
                errors.append(
                    f"{prefix}: edit-call negative failed for unexpected reason: {bad.failed}"
                )

        # Negative 4: malformed read args - call_schema_valid must fail.
        _collect_recursive_tools.cache_clear()
        _synthesize_plan_trace(
            trace_file,
            judgment=label,
            include_review=True,
            include_edit_call=False,
            include_bad_read_args=True,
            source=source,
        )
        bad = eval_mod.evaluate(sample, run_dir)
        if bad.ok:
            errors.append(
                f"{prefix}: bad-read-args negative unexpectedly passed."
            )
        else:
            blob = " | ".join(bad.failed)
            if "call_schema_valid" not in blob and "read" not in blob:
                errors.append(
                    f"{prefix}: bad-read-args negative failed for unexpected reason: {bad.failed}"
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

    gt = load_ground_truth(args.id)
    if not gt:
        print("No v1 review samples found in manifest.")
        return 1

    samples = load_review_samples(args.id)
    rows_by_id = {s["id"]: s for s in samples}

    import eval as eval_mod
    eval_mod.load_evaluators()
    exec_assert_fn = evaluators.get("exec_assert")
    if exec_assert_fn is None:
        print("ERROR: exec_assert evaluator not registered", file=sys.stderr)
        return 2

    all_errors: list[str] = []

    if args.which_pass in ("1", "both"):
        print("=" * 60)
        print("Pass 1 - in-process label oracle")
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
                for er in errs:
                    print(f"    - {er}")
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
                for er in errs:
                    print(f"    - {er}")
                all_errors.extend(errs)
            else:
                print(f"  PASS {label}")

    print()
    print("=" * 60)
    if all_errors:
        print(f"RESULT: FAIL ({len(all_errors)} error{'s' if len(all_errors) != 1 else ''})")
        return 1
    print(f"RESULT: PASS ({len(samples)} sample{'s' if len(samples) != 1 else ''} validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
