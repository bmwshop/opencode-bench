#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #29 (locate_url_prep_tokens, v3c).

Template: T2 (callers of a set).
Difficulty: hard.
Structural signature: only sample whose targets are all **module-level
functions** AND whose answer spans the **widest scope** (4 files: adapters.py,
auth.py, models.py, sessions.py). Tests bare-Name call resolution plus cross-
file, cross-class search.

    targets: requote_uri, urldefragauth, super_len, extract_cookies_to_jar
             (all module-level utility functions)
    scope:   src/requests/
    answer:  8 entries across 4 files

Usage
-----
    python3 data/scripts/derive_029_ground_truth.py [--json]
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

SAMPLE_ID = 29
DIFFICULTY = "hard"
TARGETS = ["requote_uri", "urldefragauth", "super_len", "extract_cookies_to_jar"]
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
