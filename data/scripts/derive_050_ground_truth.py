#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #50 (locate_utils_get_cluster_tokens, v3c).

Template: T2 (callers of a set).
Difficulty: hard.
Structural trait: `hard_tier_five_get_helpers_cross_file_fanin`.

    targets: ['get_auth_from_url', 'get_netrc_auth', 'get_encoding_from_headers', 'get_unicode_from_response', 'get_encodings_from_content']
    scope:   src/requests/
    answer:  7 entries across 3 file(s).

Usage
-----
    python3 data/scripts/derive_050_ground_truth.py [--json]
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

SAMPLE_ID = 50
DIFFICULTY = "hard"
TARGETS = ['get_auth_from_url', 'get_netrc_auth', 'get_encoding_from_headers', 'get_unicode_from_response', 'get_encodings_from_content']
SCOPE = 'src/requests/'


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
