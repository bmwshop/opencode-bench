#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #23 (locate_proxy_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: medium.
Structural signature: only sample where every caller is a method of the same
class (HTTPAdapter) while the anchor itself is a module-level function in a
DIFFERENT file. Tests "find a module-level helper, then find all its class-
method callers inside one adapter class".

    anchor: src/requests/utils.py::select_proxy   (module-level)
    scope:  [src/requests/utils.py, src/requests/adapters.py]
    answer: select_proxy + 3 HTTPAdapter methods  (4 entries)

Usage
-----
    python3 data/scripts/derive_023_ground_truth.py [--json]
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

SAMPLE_ID = 23
DIFFICULTY = "medium"
ANCHOR_FILE = "src/requests/utils.py"
ANCHOR_NAME = "select_proxy"
SCOPE = ["src/requests/utils.py", "src/requests/adapters.py"]


def derive():
    result = anchor_and_callers(
        anchor_file=ANCHOR_FILE,
        anchor_name=ANCHOR_NAME,
        scope=SCOPE,
        require_module_level_anchor=True,
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
