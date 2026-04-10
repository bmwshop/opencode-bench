#!/usr/bin/env python3
"""
Submit samples from samples.jsonl to opencode CLI and save traces to results/.

Usage:
    python run.py                    # run all samples
    python run.py --id 1             # run one sample
    python run.py --id 1 --id 2      # run multiple samples
    python run.py --category tool_schema
    python run.py --clean            # wipe results first
    python run.py --timeout 120      # custom timeout
"""

import subprocess
import shutil
import sys
import argparse
import time
from pathlib import Path
from common import ROOT, PROJECTS, RESULTS, load

DEFAULT_TIMEOUT = 180

_originals: dict[str, dict[str, bytes]] = {}

SKIP_DIRS = {"node_modules", "__pycache__"}


def _files(path):
    for p in path.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def snapshot(path):
    key = str(path)
    if key not in _originals:
        _originals[key] = {str(p): p.read_bytes() for p in _files(path)}


def restore(path):
    key = str(path)
    original = _originals.get(key, {})
    for item in _files(path):
        if str(item) not in original:
            try:
                item.unlink()
            except OSError:
                pass
    for item in sorted(path.rglob("*"), reverse=True):
        if any(part in SKIP_DIRS for part in item.parts):
            continue
        if item.is_dir() and not any(item.iterdir()):
            try:
                item.rmdir()
            except OSError:
                pass
    for fpath, content in original.items():
        p = Path(fpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.read_bytes() != content:
            p.write_bytes(content)


def run(sample, timeout):
    sid = sample["id"]
    name = sample.get("name", str(sid))
    project = sample.get("project", "default")
    cwd = PROJECTS / project

    if not cwd.exists():
        print(f"  SKIP #{sid} {name}: project {project}/ not found")
        return None

    restore(cwd)
    print(f"  RUN  #{sid} {name} (project={project})", end="", flush=True)
    start = time.time()

    try:
        proc = subprocess.Popen(
            ["opencode", "run", "--format", "json"]
            + (["--agent", sample["agent"]] if "agent" in sample else [])
            + [sample["prompt"]],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        elapsed = time.time() - start
        print(f"  ({elapsed:.0f}s)")
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        elapsed = time.time() - start
        print(f"  TIMEOUT ({elapsed:.0f}s)")
    except FileNotFoundError:
        print(f"\n  ERROR: opencode not found in PATH")
        sys.exit(1)

    out = RESULTS / f"{sid}_{name}.jsonl"
    out.write_text(stdout)

    if stderr.strip():
        (RESULTS / f"{sid}_{name}.err").write_text(stderr)

    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    tools = sum(1 for l in lines if '"tool_use"' in l)
    print(f"         {len(lines)} events, {tools} tool calls")

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Run specific sample(s) by ID")
    parser.add_argument("--category", help="Run all samples in a category")
    parser.add_argument("--clean", action="store_true", help="Wipe results first")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    if args.clean and RESULTS.exists():
        shutil.rmtree(RESULTS)
        print("Cleaned results/\n")

    RESULTS.mkdir(exist_ok=True)

    for d in PROJECTS.iterdir():
        if d.is_dir():
            snapshot(d)

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    print(f"Running {len(samples)} sample(s) (timeout={args.timeout}s)...\n")

    ran = 0
    skipped = 0
    for sample in samples:
        if run(sample, args.timeout):
            ran += 1
        else:
            skipped += 1

    print(f"\nDone. {ran} ran, {skipped} skipped")
    print(f"Results in {RESULTS}/")


if __name__ == "__main__":
    main()
