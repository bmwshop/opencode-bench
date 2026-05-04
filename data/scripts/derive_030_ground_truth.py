#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #30 (locate_session_merge_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: medium.
Structural signature: only sample where the anchor AND every caller live in
the **same single file** (`sessions.py`), with a mix of module-level
callers (e.g. merge_hooks) and class-method callers (Session.*). Tests
"intra-file definer-plus-caller cluster" reasoning.

    anchor: src/requests/sessions.py::merge_setting   (module-level)
    scope:  [src/requests/sessions.py]
    answer: merge_setting + merge_hooks + Session.prepare_request
            + Session.merge_environment_settings   (4 entries)

Usage
-----
    python3 data/scripts/derive_030_ground_truth.py [--json]
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

SAMPLE_ID = 30
DIFFICULTY = "medium"
ANCHOR_FILE = "src/requests/sessions.py"
ANCHOR_NAME = "merge_setting"
SCOPE = ["src/requests/sessions.py"]


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
