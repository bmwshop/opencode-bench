#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #26 (locate_hook_dispatch_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: easy.
Structural signature: only Easy-tier sample with a **cross-file, module-level
anchor**. Everything is module-level (no class prefix on the anchor) but the
caller is a method, forcing the model to resolve `dispatch_hook` as an imported
symbol in a different file.

    anchor: src/requests/hooks.py::dispatch_hook   (module-level)
    scope:  [src/requests/hooks.py, src/requests/sessions.py]
    answer: dispatch_hook + Session.send   (2 entries, 2 files)

Note: this sample was renamed from `locate_request_prep_tokens` to remove a
structural clone with #22 (same-file same-class 2-entry T1). The legacy token
list is preserved as `legacy_tokens` in data/v1_localization_criteria.json.

Usage
-----
    python3 data/scripts/derive_026_ground_truth.py [--json]
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

SAMPLE_ID = 26
DIFFICULTY = "easy"
ANCHOR_FILE = "src/requests/hooks.py"
ANCHOR_NAME = "dispatch_hook"
SCOPE = ["src/requests/hooks.py", "src/requests/sessions.py"]


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
