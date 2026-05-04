#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #48 (locate_iter_content_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: hard.
Structural trait: `anchor_with_nested_generate_closure_not_itself_a_caller`.

    anchor: src/requests/models.py::iter_content   (instance_method)
    scope:  ['src/requests/models.py']
    answer: 4 entries across 1 file(s).

Usage
-----
    python3 data/scripts/derive_048_ground_truth.py [--json]
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

SAMPLE_ID = 48
DIFFICULTY = "hard"
ANCHOR_FILE = "src/requests/models.py"
ANCHOR_NAME = "iter_content"
SCOPE = ['src/requests/models.py']
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
