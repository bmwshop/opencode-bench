#!/usr/bin/env python3
"""Smoke test for evaluators.content.exec_function under a relative _project_dir.

Regression guard for the path-doubling bug: when a caller passes a relative
`_project_dir`, the evaluator used to construct a relative `script_path`,
set the subprocess `cwd` to the same relative directory, and then have the
runner `open(script_path)` re-resolve against that cwd -- producing a
doubled-up path and a FileNotFoundError. The evaluator must defensively
resolve paths to absolute before crossing the cwd boundary.

Usage:
    python3 scripts/test_exec_function_relative_project_dir.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import evaluators  # noqa: E402
import eval as eval_mod  # noqa: E402

eval_mod.load_evaluators()
exec_function = evaluators.get("exec_function")
assert exec_function is not None, "exec_function evaluator not registered"


SOURCE_SRC = """
GREETING = "hello"

def to_str(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value)
"""

SCRIPT_SRC = """
from pkg.helpers import to_str

for v in [True, False, None, 42, 'hi']:
    print(f"input={v!r} output={to_str(v)}")
"""


def _make_workspace(td: Path) -> None:
    pkg_dir = td / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "helpers.py").write_text(SOURCE_SRC)
    (td / "demo.py").write_text(SCRIPT_SRC)


def _chk(project_dir: str) -> dict:
    return {
        "type": "exec_function",
        "_project_dir": project_dir,
        "source": "pkg/helpers.py",
        "script": "demo.py",
        "functions": ["to_str"],
        "expect_stdout_contains": [
            "input=True output=true",
            "input=False output=false",
            "input=42 output=42",
        ],
        "timeout": 10,
    }


def _run(project_dir: str, label: str) -> None:
    ok, reason = exec_function([], [], _chk(project_dir))
    print(f"  {label}: ok={ok} reason={reason}")
    assert ok, f"{label} failed: {reason}"


def test_relative_and_absolute_project_dir():
    """Both a relative and an absolute _project_dir must score the same."""
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="exec_function_test_", dir=str(cwd)) as td_str:
        td = Path(td_str)
        _make_workspace(td)

        rel = os.path.relpath(td, cwd)
        absolute = str(td.resolve())

        print("\n[test_relative_and_absolute_project_dir]")
        print(f"  workspace: {td}")
        _run(rel, f"relative _project_dir ({rel!r})")
        _run(absolute, "absolute _project_dir")


if __name__ == "__main__":
    test_relative_and_absolute_project_dir()
    print("\nOK -- exec_function tolerates relative _project_dir")
