#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #25 (locate_auth_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: medium.
Structural signature: only sample where the answer spans methods of a class
AND its mixin's callers (Session.prepare_request + SessionRedirectMixin.rebuild_auth)
plus the module-level anchor. Tests "scattered across classes" reasoning.

    anchor: src/requests/utils.py::get_netrc_auth   (module-level)
    scope:  [src/requests/utils.py, src/requests/sessions.py]
    answer: get_netrc_auth + Session.prepare_request + SessionRedirectMixin.rebuild_auth
            (3 entries, 2 classes)

Usage
-----
    python3 data/scripts/derive_025_ground_truth.py [--json]
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

SAMPLE_ID = 25
DIFFICULTY = "medium"
ANCHOR_FILE = "src/requests/utils.py"
ANCHOR_NAME = "get_netrc_auth"
SCOPE = ["src/requests/utils.py", "src/requests/sessions.py"]


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
