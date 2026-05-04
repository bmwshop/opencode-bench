#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #22 (locate_ssl_verify_tokens, v3c).

Template: T1 (anchor + direct callers).
Difficulty: easy.
Structural signature: only sample where both entries share the same class
prefix (both are methods on `HTTPAdapter`).

    anchor: src/requests/adapters.py::HTTPAdapter.cert_verify   (instance method)
    scope:  [src/requests/adapters.py]
    answer: 2 entries, both HTTPAdapter methods.

Usage
-----
    python3 data/scripts/derive_022_ground_truth.py [--json]
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

SAMPLE_ID = 22
DIFFICULTY = "easy"
ANCHOR_FILE = "src/requests/adapters.py"
ANCHOR_NAME = "cert_verify"
SCOPE = ["src/requests/adapters.py"]


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
