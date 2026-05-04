#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #27 (locate_streaming_tokens, v3c).

Template: T2 (callers of a set).
Difficulty: hard.
Structural signature: only sample where every target is an **instance method**,
so all call sites appear as `self.X(...)` or `obj.X(...)` (Attribute calls).
Exercises `Attribute` call-resolution at scale; a bare `rg 'X\\('` matches
definitions too, so the model must distinguish defs from calls.

    targets: iter_content, iter_lines, raise_for_status, close
             (all instance methods on Response)
    scope:   src/requests/   (any file; widest scope)
    answer:  8 entries across 4 files

T2 convention: target defs themselves are NOT in the answer; only their
callers. A caller that is itself a target is still excluded (prevents
chained self-references inflating the answer).

Usage
-----
    python3 data/scripts/derive_027_ground_truth.py [--json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.scripts.localization_oracle import (  # noqa: E402
    callers_of_set,
    cross_check_rg_calls_t2,
    run_derive_cli,
)

SAMPLE_ID = 27
DIFFICULTY = "hard"
TARGETS = ["iter_content", "iter_lines", "raise_for_status", "close"]
SCOPE = "src/requests/"


def derive():
    result = callers_of_set(targets=TARGETS, scope=SCOPE, exclude_target_defs=True)
    cross_check_rg_calls_t2(result)
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    run_derive_cli(
        sample_id=SAMPLE_ID,
        difficulty=DIFFICULTY,
        template="T2",
        result=derive(),
        json_only=args.json,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
