#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #43 (locate_proxy_resolution_tokens, v3c).

Template: T2 (callers of a set).
Difficulty: medium.
Structural trait: `medium_tier_proxy_resolution_three_helper_cluster`.

    targets: ['resolve_proxies', 'select_proxy', 'should_bypass_proxies']
    scope:   src/requests/
    answer:  6 entries across 3 file(s).

Usage
-----
    python3 data/scripts/derive_043_ground_truth.py [--json]
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

SAMPLE_ID = 43
DIFFICULTY = "medium"
TARGETS = ['resolve_proxies', 'select_proxy', 'should_bypass_proxies']
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
