#!/usr/bin/env python3
"""
Unified audit for every v1 structured-output localization sample (#21-#30).

Replaces the per-sample `data/scripts/audit_021_structured.py`. For each entry in
`data/v1_localization_criteria.json` marked `type: "structured_output"` the
script runs two independent passes:

Pass 1 — in-process
    * Re-derive the gold via `scripts.localization_oracle` (AST + rg cross-check).
    * Re-build the anchored regex from the fresh gold and assert it is byte-equal
      to the `file_regex_disk.pattern` stored in `data/samples_v1.jsonl`.
    * Cross-source consistency: `samples_v1.jsonl.difficulty` must equal
      `v1_localization_criteria.json[sid].difficulty` AND the spec markdown's
      `## Difficulty tier` header. Same for `structural_signature`.
    * Synthesize positive + negative `location.txt` variants and invoke the real
      `file_regex_disk` evaluator; confirm expected pass/fail.

Pass 2 — end-to-end through eval.py
    * Synthesize a minimal opencode trace that "writes" the correct gold
      `location.txt`; materialize a tempdir workspace; run `eval.evaluate()`.
      Both checks (`file_regex_disk`, `call_schema_valid`) must pass.
    * Synthesize a malformed-args trace; re-run eval. `call_schema_valid`
      must fail.

Usage
    python3 data/scripts/audit_localization_structured.py             # all 10 samples
    python3 data/scripts/audit_localization_structured.py --id 21     # one sample
    python3 data/scripts/audit_localization_structured.py --pass 1    # skip end-to-end
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import evaluators  # noqa: E402
from common import SAMPLES_V1, PROJECTS  # noqa: E402

from data.scripts.localization_oracle import (  # noqa: E402
    anchor_and_callers,
    build_pattern,
    callers_of_set,
    check_module_level_uniqueness,
    cross_check_rg_calls,
    cross_check_rg_calls_t2,
    emit_gold,
    sha256_gold,
)

V1_REQUESTS_ROOT = PROJECTS / "v1" / "requests"
MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_localization_criteria.json"
SPEC_DIR = ROOT / "data" / "specs" / "v1"


def load_samples() -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    with SAMPLES_V1.open() as f:
        for line in f:
            if not line.strip():
                continue
            s = json.loads(line)
            if s.get("type") == "structured_output":
                out[s["id"]] = s
    return out


def load_manifest() -> dict[int, dict[str, Any]]:
    raw = json.loads(MANIFEST_PATH.read_text())
    return {e["id"]: e for e in raw.get("samples", [])}


# ---------------------------------------------------------------------------
# Derivation by manifest (same logic as regen but returning gold + pattern only)
# ---------------------------------------------------------------------------


def derive_by_manifest(entry: dict[str, Any]):
    tmpl = entry["template"]
    if tmpl == "T1":
        a = entry["anchor"]
        result = anchor_and_callers(
            anchor_file=a["file"],
            anchor_name=a["name"],
            scope=entry["scope"],
            require_module_level_anchor=bool(a.get("module_level", True)),
        )
        cross_check_rg_calls(result.scope_files, a["name"], result.call_sites)
        if entry["id"] == 21:
            check_module_level_uniqueness(a["file"], "merge_", [a["name"]])
        return result
    if tmpl == "T2":
        result = callers_of_set(
            targets=entry["targets"],
            scope=entry["scope"],
            exclude_target_defs=True,
        )
        cross_check_rg_calls_t2(result)
        return result
    raise ValueError(f"unknown template {tmpl!r} on sample {entry['id']}")


# ---------------------------------------------------------------------------
# Pass 1
# ---------------------------------------------------------------------------


def pass1_one(sid: int, sample: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errs: list[str] = []

    result = derive_by_manifest(manifest)
    gold = emit_gold(result.entries)
    want_pattern = build_pattern(gold)

    got_pattern = next(
        (c["pattern"] for c in sample["checks"] if c["type"] == "file_regex_disk"),
        None,
    )
    if got_pattern != want_pattern:
        errs.append(
            f"#{sid}: stored regex differs from freshly-derived one.\n"
            f"        expected: {want_pattern!r}\n"
            f"        stored:   {got_pattern!r}"
        )

    # Cross-source consistency: difficulty + structural_signature + prompt presence
    if sample.get("difficulty") != manifest.get("difficulty"):
        errs.append(
            f"#{sid}: difficulty drift: samples_v1.jsonl={sample.get('difficulty')!r} "
            f"vs manifest={manifest.get('difficulty')!r}"
        )
    if sample.get("structural_signature") != manifest.get("structural_signature"):
        errs.append(f"#{sid}: structural_signature drift between jsonl row and manifest")

    # Check spec markdown has the difficulty header.
    spec_path = SPEC_DIR / f"{sid:03d}_{manifest['name']}.md"
    if not spec_path.is_file():
        errs.append(f"#{sid}: spec file missing: {spec_path}")
    else:
        text = spec_path.read_text()
        if f"**{manifest['difficulty']}**" not in text:
            errs.append(
                f"#{sid}: spec {spec_path.name} does not carry declared "
                f"difficulty `**{manifest['difficulty']}**`"
            )
        # Check gold appears verbatim in the spec.
        if gold.rstrip("\n") not in text:
            errs.append(f"#{sid}: spec {spec_path.name} does not embed the gold block")
        # SHA must match.
        digest = sha256_gold(gold)
        if digest not in text:
            errs.append(f"#{sid}: spec {spec_path.name} SHA-256 drift (expected {digest})")

    # Evaluator smoke test.
    check_fn = evaluators.get("file_regex_disk")
    if check_fn is None:
        errs.append(f"#{sid}: file_regex_disk evaluator not registered")
        return errs

    lines = gold.rstrip("\n").split("\n")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        def run_variant(label: str, content: str, expect_pass: bool) -> None:
            target = td_path / "location.txt"
            target.write_text(content)
            chk = {
                "type": "file_regex_disk",
                "path": "location.txt",
                "pattern": got_pattern,
                "_project_dir": str(td_path),
            }
            ok, reason = check_fn([], [], chk)
            if expect_pass and not ok:
                errs.append(f"#{sid}: positive variant {label!r} failed: {reason}")
            if not expect_pass and ok:
                errs.append(f"#{sid}: negative variant {label!r} unexpectedly passed")

        run_variant("correct+trailing_newline", gold, True)
        run_variant("correct_no_trailing_newline", gold.rstrip("\n"), True)

        if len(lines) > 1:
            run_variant("drop_first", "\n".join(lines[1:]) + "\n", False)
            run_variant("drop_last", "\n".join(lines[:-1]) + "\n", False)
            run_variant("wrong_sort", "\n".join(reversed(lines)) + "\n", False)

        run_variant("add_extra", gold + "src/requests/bogus.py::foo\n", False)

        # Class-prefix mutation: find a method entry (contains ".") and strip its class prefix.
        method_entry_idx = next(
            (i for i, e in enumerate(lines)
             if "::" in e and "." in e.split("::", 1)[1]),
            None,
        )
        if method_entry_idx is not None:
            file_path, qual = lines[method_entry_idx].split("::", 1)
            bare = qual.split(".")[-1]
            mutated = lines[:]
            mutated[method_entry_idx] = f"{file_path}::{bare}"
            run_variant("strip_class_prefix", "\n".join(mutated) + "\n", False)

        # Path mutation: add leading "./" to every entry.
        mutated_paths = [e.replace("src/requests/", "./src/requests/") for e in lines]
        run_variant("leading_dot_slash", "\n".join(mutated_paths) + "\n", False)

    return errs


# ---------------------------------------------------------------------------
# Pass 2 (end-to-end through eval.py)
# ---------------------------------------------------------------------------


def _synthesize_trace(trace_path: Path, correct: bool, gold: str) -> None:
    if correct:
        tool_input = {"filePath": "location.txt", "content": gold}
    else:
        tool_input = {"path": "location.txt", "content": gold}  # schema violation
    events = [
        {"type": "step_start"},
        {
            "type": "tool_use",
            "part": {
                "tool": "write",
                "state": {"input": tool_input, "output": "ok"},
            },
        },
        {"type": "text", "part": {"text": "Wrote location.txt"}},
    ]
    trace_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def pass2_one(sid: int, sample: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errs: list[str] = []

    result = derive_by_manifest(manifest)
    gold = emit_gold(result.entries)

    import eval as eval_mod
    from common import run_project_name, trace_name
    from evaluators._recursive import _collect_recursive_tools

    eval_mod.load_evaluators()

    with tempfile.TemporaryDirectory(prefix=f"audit_{sid:03d}_") as td:
        run_dir = Path(td)
        proj_dir = run_dir / "projects" / run_project_name(sample)
        shutil.copytree(V1_REQUESTS_ROOT, proj_dir, dirs_exist_ok=False, symlinks=True)
        (proj_dir / "location.txt").write_text(gold)

        trace_file = run_dir / f"{trace_name(sample)}.jsonl"

        _synthesize_trace(trace_file, correct=True, gold=gold)
        _collect_recursive_tools.cache_clear()
        result_ok = eval_mod.evaluate(sample, run_dir)
        if not result_ok.ok:
            errs.append(
                f"#{sid}: positive end-to-end failed. "
                f"passed={result_ok.passed} failed={result_ok.failed}"
            )

        _synthesize_trace(trace_file, correct=False, gold=gold)
        _collect_recursive_tools.cache_clear()
        result_bad = eval_mod.evaluate(sample, run_dir)
        if result_bad.ok:
            errs.append(
                f"#{sid}: malformed-args negative unexpectedly passed "
                f"(expected call_schema_valid failure). passed={result_bad.passed}"
            )
        else:
            blob = " | ".join(result_bad.failed)
            if "call_schema_valid" not in blob and "write" not in blob:
                errs.append(
                    f"#{sid}: malformed-args negative failed for unexpected reason: "
                    f"{result_bad.failed}"
                )

    return errs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", type=int, action="append")
    p.add_argument(
        "--pass", dest="which_pass", choices=["1", "2", "both"], default="both"
    )
    args = p.parse_args()

    import eval as eval_mod  # noqa: E402
    eval_mod.load_evaluators()

    samples = load_samples()
    manifest = load_manifest()

    ids = sorted(samples.keys())
    if args.id:
        ids = [i for i in ids if i in args.id]
    if not ids:
        print("no matching structured-output samples found")
        return 2

    all_errors: list[str] = []

    for sid in ids:
        sample = samples[sid]
        entry = manifest.get(sid)
        if not entry:
            all_errors.append(f"#{sid}: no manifest entry for sample")
            continue

        print("=" * 60)
        print(f"#{sid} {entry['name']}  [{entry['difficulty']}, {entry['template']}]")
        print("=" * 60)

        if args.which_pass in ("1", "both"):
            print("  Pass 1 (in-process)  ... ", end="", flush=True)
            errs = pass1_one(sid, sample, entry)
            if errs:
                print("FAIL")
                for e in errs:
                    print(f"    - {e}")
                all_errors.extend(errs)
            else:
                print("PASS")

        if args.which_pass in ("2", "both"):
            print("  Pass 2 (end-to-end)  ... ", end="", flush=True)
            errs = pass2_one(sid, sample, entry)
            if errs:
                print("FAIL")
                for e in errs:
                    print(f"    - {e}")
                all_errors.extend(errs)
            else:
                print("PASS")
        print()

    print("=" * 60)
    if all_errors:
        print(f"RESULT: FAIL ({len(all_errors)} error{'s' if len(all_errors) != 1 else ''})")
        return 1
    print(f"RESULT: PASS ({len(ids)} structured sample(s) audited)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
