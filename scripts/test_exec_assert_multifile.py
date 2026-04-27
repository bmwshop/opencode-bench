#!/usr/bin/env python3
"""Smoke test for evaluators.content.exec_assert in both shapes.

Single-file (legacy) and multi-file `targets` forms must both work; symbol
collisions across multi-file targets must be rejected up front.

Usage:
    python3 scripts/test_exec_assert_multifile.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import evaluators  # noqa: E402
import eval as eval_mod  # noqa: E402

eval_mod.load_evaluators()
exec_assert = evaluators.get("exec_assert")
assert exec_assert is not None, "exec_assert evaluator not registered"


FILE_A = """
GREETING = "hello"

def greet(name):
    return f"{GREETING}, {name}"
"""

FILE_B = """
def shout(s):
    return s.upper() + "!"
"""

FILE_COLLISION = """
def greet(name):
    return f"goodbye, {name}"  # collides with file_a's greet
"""


def _td_with_files(files):
    td = tempfile.mkdtemp(prefix="exec_assert_test_")
    for rel, src in files.items():
        p = Path(td) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
    return td


def test_single_file_legacy_shape():
    td = _td_with_files({"a.py": FILE_A})
    chk = {
        "type": "exec_assert",
        "_project_dir": td,
        "path": "a.py",
        "constants": ["GREETING"],
        "functions": ["greet"],
        "imports": [],
        "asserts": [
            {"expr": "GREETING == 'hello'"},
            {"expr": "greet('world') == 'hello, world'"},
        ],
        "timeout": 5,
    }
    ok, reason = exec_assert([], [], chk)
    assert ok, f"legacy single-file form failed: {reason}"
    print("  PASS legacy single-file form")


def test_multi_file_targets_shape():
    td = _td_with_files({"a.py": FILE_A, "b.py": FILE_B})
    chk = {
        "type": "exec_assert",
        "_project_dir": td,
        "targets": [
            {
                "path": "a.py",
                "constants": ["GREETING"],
                "functions": ["greet"],
                "imports": [],
            },
            {
                "path": "b.py",
                "constants": [],
                "functions": ["shout"],
                "imports": [],
            },
        ],
        "asserts": [
            {"expr": "shout(greet('world')) == 'HELLO, WORLD!'"},
        ],
        "timeout": 5,
    }
    ok, reason = exec_assert([], [], chk)
    assert ok, f"multi-file targets form failed: {reason}"
    print("  PASS multi-file targets form")


def test_multi_file_collision_rejected():
    td = _td_with_files({"a.py": FILE_A, "c.py": FILE_COLLISION})
    chk = {
        "type": "exec_assert",
        "_project_dir": td,
        "targets": [
            {"path": "a.py", "functions": ["greet"]},
            {"path": "c.py", "functions": ["greet"]},
        ],
        "asserts": [{"expr": "greet('x') == 'hello, x'"}],
        "timeout": 5,
    }
    ok, reason = exec_assert([], [], chk)
    assert not ok, "collision check did not fire"
    assert "greet" in (reason or ""), f"reason should name the colliding symbol: {reason!r}"
    assert "collision" in (reason or "").lower(), f"reason should mention collision: {reason!r}"
    print("  PASS multi-file collision rejected")


def test_multi_file_assert_failure_localized():
    td = _td_with_files({"a.py": FILE_A, "b.py": FILE_B})
    chk = {
        "type": "exec_assert",
        "_project_dir": td,
        "targets": [
            {"path": "a.py", "constants": ["GREETING"], "functions": ["greet"]},
            {"path": "b.py", "functions": ["shout"]},
        ],
        "asserts": [
            {"expr": "shout(greet('world')) == 'HOWDY!'"},  # intentional fail
        ],
        "timeout": 5,
    }
    ok, reason = exec_assert([], [], chk)
    assert not ok, "expected failing assert"
    assert "shout(greet('world'))" in (reason or ""), f"reason should name the failing assert: {reason!r}"
    print("  PASS multi-file failing assert reports correctly")


def main():
    print("exec_assert smoke tests")
    print("-" * 40)
    test_single_file_legacy_shape()
    test_multi_file_targets_shape()
    test_multi_file_collision_rejected()
    test_multi_file_assert_failure_localized()
    print("-" * 40)
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
