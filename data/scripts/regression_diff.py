#!/usr/bin/env python3
"""Regression diff for sample migration.

Two-pass flow:
  pass 1 (pre): check out HEAD:data/samples_v0.jsonl, eval every run, snapshot
  pass 2 (post): restore the working-tree samples_v0.jsonl, eval every run

Diffs pass/fail + failed-reason lists for migrated samples across the two
passes and prints PASS<->FAIL flips plus any reason-only changes. Restores the
working-tree JSONL at the end.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
RUNS = REPO / "runs" / "v0"
EVAL = REPO / "eval.py"
SAMPLES = REPO / "data" / "samples_v0.jsonl"

MIGRATED_IDS = {3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 22, 25, 26, 27, 28, 31, 32, 33}


def _sid(label):
    if not label.startswith("#"):
        return None
    try:
        return int(label.split()[0][1:])
    except (ValueError, IndexError):
        return None


def index(scores):
    out = {}
    for s in scores.get("samples", []):
        sid = _sid(s.get("label", ""))
        if sid is not None:
            out[sid] = s
    return out


def fmt_reasons(s):
    return sorted(s.get("failed", []))


def eval_all_runs():
    """Return {(model, run_ts): scores_dict} for every run, using the samples
    file currently on disk. Side-effect: overwrites each run's scores.json."""
    out = {}
    for run_dir in sorted(p.parent for p in RUNS.rglob("scores.json")):
        meta_path = run_dir / "meta.json"
        scores_path = run_dir / "scores.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        model = meta.get("model")
        run_ts = run_dir.name
        if not model:
            continue
        r = subprocess.run(
            [sys.executable, str(EVAL), "--model", model, "--run", run_ts, "--format", "json"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            print(f"!! eval failed for {model}/{run_ts}: {r.stderr[:400]}", file=sys.stderr)
            continue
        out[(model, run_ts)] = json.loads(scores_path.read_text())
    return out


def main():
    post_samples = SAMPLES.read_bytes()
    pre_samples = subprocess.check_output(
        ["git", "show", "HEAD:data/samples_v0.jsonl"],
        cwd=REPO,
    )

    try:
        SAMPLES.write_bytes(pre_samples)
        print("[pass 1] evaluating pre-migration samples...", file=sys.stderr)
        pre = eval_all_runs()

        SAMPLES.write_bytes(post_samples)
        print("[pass 2] evaluating post-migration samples...", file=sys.stderr)
        post = eval_all_runs()
    finally:
        SAMPLES.write_bytes(post_samples)

    flips_pf = []
    flips_fp = []
    reason_changes = []

    for key in sorted(post.keys() & pre.keys()):
        model, ts = key
        pre_idx = index(pre[key])
        post_idx = index(post[key])
        for sid in sorted(MIGRATED_IDS):
            b = pre_idx.get(sid)
            f = post_idx.get(sid)
            if b is None or f is None:
                continue
            b_ok = bool(b.get("pass"))
            f_ok = bool(f.get("pass"))
            if b_ok and not f_ok:
                flips_pf.append((model, ts, sid, b, f))
            elif f_ok and not b_ok:
                flips_fp.append((model, ts, sid, b, f))
            else:
                b_reasons = fmt_reasons(b)
                f_reasons = fmt_reasons(f)
                if b_reasons != f_reasons:
                    reason_changes.append((model, ts, sid, b_reasons, f_reasons))

    print()
    print("=" * 72)
    print(f"Regression diff across {len(post.keys() & pre.keys())} runs, "
          f"{len(MIGRATED_IDS)} migrated samples")
    print("=" * 72)
    print()
    print(f"PASS->FAIL flips: {len(flips_pf)}")
    for model, ts, sid, b, f in flips_pf:
        print(f"  {model}/{ts} {f.get('label')}")
        for r in fmt_reasons(f):
            print(f"     NOW FAILING: {r}")

    print()
    print(f"FAIL->PASS flips: {len(flips_fp)}")
    for model, ts, sid, b, f in flips_fp:
        print(f"  {model}/{ts} {f.get('label')}")
        for r in fmt_reasons(b):
            print(f"     was failing: {r}")

    print()
    print(f"Reason-only changes (same pass/fail): {len(reason_changes)}")
    if "-v" in sys.argv:
        for model, ts, sid, b_r, f_r in reason_changes:
            print(f"  {model}/{ts} #{sid}")
            for r in b_r:
                print(f"     - {r}")
            for r in f_r:
                print(f"     + {r}")


if __name__ == "__main__":
    main()
