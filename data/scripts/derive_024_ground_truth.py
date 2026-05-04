#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #24 (locate_redirect_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: easy.
Structural signature: only sample where scope is a single file AND the answer
contains a mixin method (SessionRedirectMixin.resolve_redirects) alongside a
subclass method (Session.send).

    anchor: src/requests/sessions.py::SessionRedirectMixin.resolve_redirects
            (instance method on mixin)
    scope:  [src/requests/sessions.py]
    answer: the mixin method + Session.send  (2 entries, 2 classes)

Usage
-----
    python3 data/scripts/derive_024_ground_truth.py [--json]
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

SAMPLE_ID = 24
DIFFICULTY = "easy"
ANCHOR_FILE = "src/requests/sessions.py"
ANCHOR_NAME = "resolve_redirects"
SCOPE = ["src/requests/sessions.py"]


def derive():
    result = anchor_and_callers(
        anchor_file=ANCHOR_FILE,
        anchor_name=ANCHOR_NAME,
        scope=SCOPE,
        require_module_level_anchor=False,
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
