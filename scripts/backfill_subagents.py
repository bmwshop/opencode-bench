#!/usr/bin/env python3
"""
Backfill `{stem}.subagent-{sid[-10:]}.json` sidecars for every parent trace
already in `runs/v0/*/*/`. Reuses `run.py:_capture_subagents`, which shells out
to `opencode export` against the local SQLite store at
`~/.local/share/opencode/opencode.db`. Idempotent: existing sidecars are
overwritten, missing ones are skipped with a WARN.

Usage:
    python scripts/backfill_subagents.py                 # all v0 runs
    python scripts/backfill_subagents.py --version v1    # v1 runs
    python scripts/backfill_subagents.py --dry-run       # just list candidates
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run import _capture_subagents  # noqa: E402
from common import RUNS, resolve_opencode_cmd  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v0", choices=["v0", "v1"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    argv, _, oc_cwd = resolve_opencode_cmd()
    root = Path(__file__).resolve().parents[1]
    cwd = Path(oc_cwd) if oc_cwd else root

    traces = sorted((RUNS / args.version).glob("*/*/*.jsonl"))
    parents = [t for t in traces if ".subagent-" not in t.name]
    print(f"Found {len(parents)} parent traces under {RUNS / args.version}")

    hits = 0
    for t in parents:
        text = t.read_text(errors="ignore")
        if '"tool":"task"' not in text:
            continue
        hits += 1
        print(f"  {t.relative_to(root)}")
        if args.dry_run:
            continue
        _capture_subagents(t, cwd, argv)
    print(f"\n{hits} trace(s) with task calls" + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
