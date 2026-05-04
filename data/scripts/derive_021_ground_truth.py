#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #21 (locate_cookie_tokens, v3c).

v3c = v3b prompt wording + dotted qualname gold format.

Template: T1 (anchor + direct callers).
Difficulty: easy.
Gold SHA-256: 595ff5abc90046941c112e8d12b6ab9ca9a819aaf8b8d09f38d94544e93a9762

Verification layers (shared via data/scripts/localization_oracle.py):
    1. AST anchor+callers derivation.
    2. `rg -n -w --with-filename merge_cookies <scope>` cross-check.
    3. Module-level uniqueness of part (A): the only module-level `merge_*`
       function in cookies.py is `merge_cookies`.

Usage
-----
    python3 data/scripts/derive_021_ground_truth.py [--json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.scripts.localization_oracle import (  # noqa: E402
    anchor_and_callers,
    check_module_level_uniqueness,
    cross_check_rg_calls,
    run_derive_cli,
)

SAMPLE_ID = 21
DIFFICULTY = "easy"
ANCHOR_FILE = "src/requests/cookies.py"
ANCHOR_NAME = "merge_cookies"
SCOPE = ["src/requests/cookies.py", "src/requests/sessions.py"]


def derive():
    result = anchor_and_callers(
        anchor_file=ANCHOR_FILE,
        anchor_name=ANCHOR_NAME,
        scope=SCOPE,
        require_module_level_anchor=True,
    )
    cross_check_rg_calls(result.scope_files, ANCHOR_NAME, result.call_sites)
    check_module_level_uniqueness(ANCHOR_FILE, "merge_", [ANCHOR_NAME])
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
        extra_checks=["module-level uniqueness"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
