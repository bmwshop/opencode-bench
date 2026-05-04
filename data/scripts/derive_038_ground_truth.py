#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #38 (locate_basic_auth_str_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: medium.
Structural trait: `basic_auth_string_builder_fanin_across_auth_adapter_session`.

    anchor: src/requests/auth.py::_basic_auth_str   (module_level)
    scope:  ['src/requests/adapters.py', 'src/requests/auth.py', 'src/requests/sessions.py']
    answer: 5 entries across 3 file(s).

Usage
-----
    python3 data/scripts/derive_038_ground_truth.py [--json]
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

SAMPLE_ID = 38
DIFFICULTY = "medium"
ANCHOR_FILE = "src/requests/auth.py"
ANCHOR_NAME = "_basic_auth_str"
SCOPE = ['src/requests/adapters.py', 'src/requests/auth.py', 'src/requests/sessions.py']
REQUIRE_MODULE_LEVEL = True


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
