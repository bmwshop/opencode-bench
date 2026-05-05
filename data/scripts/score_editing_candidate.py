#!/usr/bin/env python3
"""
Score an editing-sample candidate stub end-to-end.

Given a JSON file shaped like a manifest entry from
`data/scripts/json/v1_editing_criteria.json` (with optional extras like `mutants[]`,
`leak_function_name`, and a multi-file `targets` shape), run every cheap
correctness gate and report.

Gates run
---------
  L1  reference edit `oldString` is unique in the baseline file(s) AND
      every assert passes against the patched file(s).
  L2  baseline (un-patched) FAILS the full assert list (otherwise
      new_behavior asserts test nothing).
  L2b every regression-only sub-list PASSES against the baseline (so
      regression asserts don't accidentally encode post-edit state).
  L3  for each declared `mutants[]` entry (a misstep mutation patch),
      applying it to the baseline must FAIL >= 1 assert.
  L6  multi-file only: applying just one of the targets' patches must
      FAIL >= 1 assert (proves the cross-file edit is genuinely required).

Each gate's pass/fail is reported in the JSON output. Exit code is 0
when every gate passes, 1 otherwise. The script never mutates the
on-disk fixture; everything runs in tempdirs.

Expected candidate JSON
-----------------------

Single-file::

    {
      "id": 51,
      "name": "edit_iter_slices_require_positive",
      "file": "src/requests/utils.py",
      "functions": ["iter_slices"],
      "constants": [],
      "imports": [],
      "reference_edit": {"oldString": "...", "newString": "..."},
      "asserts": [{"expr": "...", "kind": "regression", "misstep": "no-change"}, ...],
      "mutants": [
        {"misstep": "no-change", "patch": null},
        {"misstep": "over-edit", "patch": {"oldString": "...", "newString": "..."}}
      ]
    }

Multi-file::

    {
      "id": 53,
      ...
      "targets": [
        {"path": "src/a.py", "functions": [...], "constants": [...], "imports": [...],
         "reference_edit": {"oldString": "...", "newString": "..."}},
        {"path": "src/b.py", "functions": [...], "constants": [...], "imports": [...],
         "reference_edit": {"oldString": "...", "newString": "..."}}
      ],
      "asserts": [...],
      "mutants": [...]
    }
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import evaluators  # noqa: E402
import eval as eval_mod  # noqa: E402

eval_mod.load_evaluators()
exec_assert = evaluators.get("exec_assert")
assert exec_assert is not None, "exec_assert evaluator not registered"

V1_REPOS_PATH = ROOT / "data" / "v1_repos.json"
DEFAULT_REPO = "requests"


def _load_v1_repos() -> dict:
    return json.loads(V1_REPOS_PATH.read_text())


def repo_root(slug: str) -> Path:
    repos = _load_v1_repos()
    if slug not in repos:
        raise ValueError(
            f"unknown repo {slug!r}; v1_repos.json knows: {sorted(repos)}"
        )
    return ROOT / repos[slug]["submodule_path"]


# ---------------------------------------------------------------------------
# Candidate normalization
# ---------------------------------------------------------------------------


def _normalize(candidate: dict) -> dict:
    """Return a uniform shape:

        {"targets": [{"path", "functions", "constants", "imports", "reference_edit"}, ...],
         "asserts": [...], "mutants": [...]}.

    Single-file inputs are converted to a one-element targets list.
    """
    if candidate.get("targets"):
        return candidate
    return {
        **candidate,
        "targets": [{
            "path": candidate["file"],
            "functions": candidate.get("functions", []),
            "constants": candidate.get("constants", []),
            "imports": candidate.get("imports", []),
            "reference_edit": candidate["reference_edit"],
        }],
    }


def _strip_assert_fields(asserts: list) -> list:
    return [{k: v for k, v in a.items() if k in ("expr", "setup")} for a in asserts]


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _materialize(td: Path, targets: list[dict], variant: dict[str, str],
                 slug: str = DEFAULT_REPO) -> None:
    """Copy each target file into td and apply the patch denoted in `variant`.

    `variant` maps target path -> "patched" | "baseline" so the caller can
    request mixed states (e.g. apply A only, leave B as baseline).
    """
    root = repo_root(slug)
    for t in targets:
        rel = t["path"]
        src = (root / rel).read_text()
        body = src
        if variant.get(rel) == "patched":
            ed = t["reference_edit"]
            count = src.count(ed["oldString"])
            if count != 1:
                raise ValueError(f"{rel}: oldString occurs {count} times (need 1)")
            body = src.replace(ed["oldString"], ed["newString"], 1)
        out = td / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)


def _apply_mutant(td: Path, mutant: dict, default_target_path: str) -> None:
    patch = mutant.get("patch")
    if not patch:  # `no-change` mutants are simply the baseline
        return
    rel = patch.get("path") or default_target_path
    out = td / rel
    src = out.read_text()
    old = patch["oldString"]
    new = patch["newString"]
    count = src.count(old)
    if count != 1:
        raise ValueError(
            f"mutant {mutant.get('misstep')!r}: oldString occurs {count} times in {rel}"
        )
    out.write_text(src.replace(old, new, 1))


def _exec_assert_chk(td: Path, c: dict) -> dict:
    """Build an exec_assert chk from the normalized candidate, rooted at td."""
    if len(c["targets"]) == 1:
        t = c["targets"][0]
        return {
            "type": "exec_assert",
            "_project_dir": str(td),
            "path": t["path"],
            "functions": list(t.get("functions", [])),
            "constants": list(t.get("constants", []) or []),
            "imports": list(t.get("imports", []) or []),
            "asserts": _strip_assert_fields(c["asserts"]),
            "timeout": 10,
        }
    return {
        "type": "exec_assert",
        "_project_dir": str(td),
        "targets": [
            {
                "path": t["path"],
                "functions": list(t.get("functions", [])),
                "constants": list(t.get("constants", []) or []),
                "imports": list(t.get("imports", []) or []),
            }
            for t in c["targets"]
        ],
        "asserts": _strip_assert_fields(c["asserts"]),
        "timeout": 10,
    }


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def _all_patched(c: dict) -> dict[str, str]:
    return {t["path"]: "patched" for t in c["targets"]}


def _all_baseline(c: dict) -> dict[str, str]:
    return {t["path"]: "baseline" for t in c["targets"]}


def _slug(c: dict) -> str:
    return c.get("repo") or DEFAULT_REPO


def gate_l1(c: dict) -> dict:
    """L1: reference applies cleanly + all asserts pass on patched."""
    with tempfile.TemporaryDirectory(prefix="l1_") as td:
        td_path = Path(td)
        try:
            _materialize(td_path, c["targets"], _all_patched(c), _slug(c))
        except ValueError as e:
            return {"name": "L1", "ok": False, "reason": str(e)}
        ok, reason = exec_assert([], [], _exec_assert_chk(td_path, c))
        return {"name": "L1", "ok": ok, "reason": reason}


def gate_l2(c: dict) -> dict:
    """L2: full assert list FAILS against the un-patched baseline."""
    with tempfile.TemporaryDirectory(prefix="l2_") as td:
        td_path = Path(td)
        _materialize(td_path, c["targets"], _all_baseline(c), _slug(c))
        ok, reason = exec_assert([], [], _exec_assert_chk(td_path, c))
        if ok:
            return {"name": "L2", "ok": False,
                    "reason": "baseline unexpectedly passed full assert list (asserts may not require the change)"}
        return {"name": "L2", "ok": True, "reason": None}


def gate_l2b(c: dict) -> dict:
    """L2b: regression-only subset PASSES against the baseline."""
    reg = [a for a in c["asserts"] if a.get("kind") == "regression"]
    if not reg:
        return {"name": "L2b", "ok": True, "reason": "no regression asserts to check"}
    with tempfile.TemporaryDirectory(prefix="l2b_") as td:
        td_path = Path(td)
        _materialize(td_path, c["targets"], _all_baseline(c), _slug(c))
        sub = copy.deepcopy(c)
        sub["asserts"] = reg
        ok, reason = exec_assert([], [], _exec_assert_chk(td_path, sub))
        if not ok:
            return {"name": "L2b", "ok": False,
                    "reason": f"regression asserts fail on baseline (likely depend on post-edit state): {reason}"}
        return {"name": "L2b", "ok": True, "reason": None}


def gate_l3(c: dict) -> dict:
    """L3: every declared mutant must FAIL >= 1 assert."""
    mutants = c.get("mutants", [])
    if not mutants:
        return {"name": "L3", "ok": True, "reason": "no mutants declared (skipped)"}
    if len(mutants) < 2:
        return {"name": "L3", "ok": False,
                "reason": f"need >=2 mutants to validate assert tightness; got {len(mutants)}"}
    failures = []
    for m in mutants:
        with tempfile.TemporaryDirectory(prefix="l3_") as td:
            td_path = Path(td)
            _materialize(td_path, c["targets"], _all_baseline(c), _slug(c))
            try:
                _apply_mutant(td_path, m, c["targets"][0]["path"])
            except ValueError as e:
                failures.append(f"{m.get('misstep')}: mutant could not be applied ({e})")
                continue
            ok, reason = exec_assert([], [], _exec_assert_chk(td_path, c))
            if ok:
                failures.append(f"{m.get('misstep')}: mutant unexpectedly passed all asserts")
    if failures:
        return {"name": "L3", "ok": False, "reason": "; ".join(failures)}
    return {"name": "L3", "ok": True, "reason": f"{len(mutants)} mutants caught"}


def gate_l6(c: dict) -> dict:
    """L6: hard-tier multi-file. Each single-patch variant must FAIL."""
    if len(c["targets"]) < 2:
        return {"name": "L6", "ok": True, "reason": "single-file (skipped)"}
    failures = []
    for i, t in enumerate(c["targets"]):
        variant = {x["path"]: "baseline" for x in c["targets"]}
        variant[t["path"]] = "patched"
        with tempfile.TemporaryDirectory(prefix="l6_") as td:
            td_path = Path(td)
            _materialize(td_path, c["targets"], variant, _slug(c))
            ok, _ = exec_assert([], [], _exec_assert_chk(td_path, c))
            if ok:
                failures.append(
                    f"applying only target #{i} ({t['path']}) passed all asserts; "
                    f"the cross-file edit is not required"
                )
    if failures:
        return {"name": "L6", "ok": False, "reason": "; ".join(failures)}
    return {"name": "L6", "ok": True, "reason": "both single-patch variants caught"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("candidate", help="path to candidate JSON")
    p.add_argument("--format", choices=["json", "text"], default="text")
    args = p.parse_args()

    raw = json.loads(Path(args.candidate).read_text())
    c = _normalize(raw)

    gates = [gate_l1, gate_l2, gate_l2b, gate_l3, gate_l6]
    results = [g(c) for g in gates]
    overall_ok = all(r["ok"] for r in results)

    payload = {
        "id": c.get("id"),
        "name": c.get("name"),
        "targets": [t["path"] for t in c["targets"]],
        "n_asserts": len(c.get("asserts", [])),
        "n_mutants": len(c.get("mutants", [])),
        "gates": results,
        "ok": overall_ok,
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(f"Candidate #{payload['id']} {payload['name']!r}")
        print(f"  targets:  {', '.join(payload['targets'])}")
        print(f"  asserts:  {payload['n_asserts']}, mutants: {payload['n_mutants']}")
        for r in results:
            tag = "PASS" if r["ok"] else "FAIL"
            line = f"  {tag} {r['name']}"
            if r.get("reason"):
                line += f"  - {r['reason']}"
            print(line)
        print()
        print("RESULT:", "OK" if overall_ok else "FAIL")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
