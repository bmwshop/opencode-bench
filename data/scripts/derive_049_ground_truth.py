#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #49 (locate_digest_header_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: hard.
Structural trait: `digest_header_builder_with_nested_sha_helper_and_challenge_retry`.

    anchor: src/requests/auth.py::build_digest_header   (instance_method)
    scope:  ['src/requests/auth.py']
    answer: 3 entries across 1 file(s).

Usage
-----
    python3 data/scripts/derive_049_ground_truth.py [--json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.scripts.localization_oracle import (  # noqa: E402
    anchor_and_callers,
    cross_check_rg_calls,
    run_derive_cli,
)

SAMPLE_ID = 49
DIFFICULTY = "hard"
ANCHOR_FILE = "src/requests/auth.py"
ANCHOR_NAME = "build_digest_header"
SCOPE = ['src/requests/auth.py']
REQUIRE_MODULE_LEVEL = False


def derive():
    result = anchor_and_callers(
        anchor_file=ANCHOR_FILE,
        anchor_name=ANCHOR_NAME,
        scope=SCOPE,
        require_module_level_anchor=REQUIRE_MODULE_LEVEL,
    )
    cross_check_rg_calls(result.scope_files, ANCHOR_NAME, result.call_sites)
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    run_derive_cli(
        sample_id=SAMPLE_ID,
        difficulty=DIFFICULTY,
        template="T1",
        result=derive(),
        json_only=args.json,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
