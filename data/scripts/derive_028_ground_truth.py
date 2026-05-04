#!/usr/bin/env python3
"""
Derive + verify the ground-truth for v1 sample #28 (locate_exception_tokens, v3c).

Template: T2 (callers of a set; constructor semantics).
Difficulty: hard.
Structural signature: only sample where the targets are **exception classes**
(not functions), so all "calls" appear in `raise X(...)` positions. Tests
constructor-vs-function-call semantics. ALSO the only sample whose answer
contains a nested closure function (`Response.iter_content.generate`),
testing the dotted-qualname policy for nested `def`s.

    targets: ConnectionError, HTTPError, InvalidURL, TooManyRedirects
             (all subclasses of RequestException)
    scope:   src/requests/
    answer:  8 entries across 4 files (including `Response.iter_content.generate`)

Note: AST treats `raise Foo(...)` as an `ast.Raise` wrapping an `ast.Call`
with `func=Name('Foo')`. Our oracle classifies that as a call by name to
`Foo`, so constructor-raise sites are captured the same way regular calls
are. This is intentional and documented in the prompt.

Usage
-----
    python3 data/scripts/derive_028_ground_truth.py [--json]
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

SAMPLE_ID = 28
DIFFICULTY = "hard"
TARGETS = ["ConnectionError", "HTTPError", "InvalidURL", "TooManyRedirects"]
SCOPE = "src/requests/"


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
