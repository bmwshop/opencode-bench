#!/usr/bin/env python3
"""
Convert legacy v1 ``scores.json`` files to the post-suspension shape so old
runs stay comparable with current runs without re-running them.

What it does (and only this):

  * Drops per-sample entries with id in {12, 13, 14, 15} (the v0.5 archive).
  * Drops the ``code_authoring`` category (now empty) from ``categories``.
  * Recomputes per-category aggregates (strict, total, partial, efficiency,
    efficiency_n, checks_passed, checks_total, by_difficulty) from the
    surviving per-sample dicts.
  * Recomputes the headline aggregates (strict, total, partial,
    strict_completed, total_completed, partial_completed, efficiency,
    efficiency_n, timed_out, checks_passed, checks_total) the same way
    ``eval.build()`` does.
  * Leaves ``run`` metadata and per-sample fields untouched.

What it does NOT do:

  * It does not re-grade. If a sample's per-sample score in the source
    ``scores.json`` predates a grader fix (e.g. exec_function path-doubling,
    #45 narrowing, #430 regex relaxation), the converted output will carry
    the same stale per-sample score forward. To pick up grader fixes you
    must rerun ``eval.py`` against the existing trace files.

Default behaviour (``python scripts/convert_scores_post_suspension.py``):

  * Walks ``runs/v1/**/scores.json`` under the repo root. Override with
    ``--results-root PATH`` to walk a different tree (e.g. shared lustre
    results), or pass explicit positional paths to convert just those.
  * Skips files modified before the latest grader fix (2026-04-29 12:00
    local) so legacy buggy scores aren't promoted as if they were current.
    Use ``--all-runs`` or ``--since`` to override.
  * Skips files that are already in post-suspension shape (idempotent).
  * Backs up the original to ``scores.json.pre-v0.5.bak`` then rewrites
    ``scores.json`` in place. ``--no-backup`` to skip the backup.
  * Prints one summary line per file.

Examples:
    python scripts/convert_scores_post_suspension.py
    python scripts/convert_scores_post_suspension.py --dry-run
    python scripts/convert_scores_post_suspension.py --all-runs
    python scripts/convert_scores_post_suspension.py --since 2026-04-29
    python scripts/convert_scores_post_suspension.py runs/v1/<model>/<ts>/scores.json
    python scripts/convert_scores_post_suspension.py \\
        --results-root /lustre/.../smajumdar/results/opencode_paper/v1 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SUSPENDED_IDS = {12, 13, 14, 15}
SUSPENDED_CATEGORY = "code_authoring"

DEFAULT_SINCE = datetime(2026, 4, 29, 12, 0, 0)
DEFAULT_RESULTS_ROOT = REPO_ROOT / "runs" / "v1"
SCORES_GLOB = "**/scores.json"
BACKUP_SUFFIX = ".pre-v0.5.bak"

LABEL_RE = re.compile(r"^#(\d+)\s")
DIFFICULTY_ORDER = ("easy", "medium", "hard")


def sample_id(sample: dict) -> int | None:
    """Extract the leading numeric id from a sample's label, e.g. ``#42``."""
    label = sample.get("label", "")
    m = LABEL_RE.match(label)
    return int(m.group(1)) if m else None


def is_already_converted(scores: dict) -> bool:
    """A file is already in post-suspension shape if no suspended ids appear
    in its samples list and ``code_authoring`` is absent from categories."""
    if SUSPENDED_CATEGORY in scores.get("categories", {}):
        return False
    for s in scores.get("samples", []):
        if sample_id(s) in SUSPENDED_IDS:
            return False
    return True


def _bucket_by_difficulty(samples: list[dict]) -> dict[str, dict]:
    """Mirror ``eval._bucket_by_difficulty`` but operate on dict samples."""
    buckets: dict[str, list[dict]] = {}
    for s in samples:
        tier = s.get("difficulty")
        if not tier:
            continue
        buckets.setdefault(tier, []).append(s)
    out: dict[str, dict] = {}

    def _emit(tier: str, ss: list[dict]) -> None:
        total = len(ss)
        if total == 0:
            return
        strict = sum(1 for s in ss if s.get("pass"))
        partial = sum(s.get("score", 0.0) for s in ss) / total
        out[tier] = {
            "strict": strict,
            "total": total,
            "partial": round(partial, 4),
        }

    for tier in DIFFICULTY_ORDER:
        ss = buckets.get(tier)
        if ss:
            _emit(tier, ss)
    for tier, ss in buckets.items():
        if tier not in out:
            _emit(tier, ss)
    return out


def _efficiency(samples: list[dict]) -> tuple[float | None, int]:
    """Mirror ``eval._efficiency``: mean of min(min/recursive, 1.0) over
    strict-passing samples with both counts positive."""
    vals = []
    for s in samples:
        if not s.get("pass"):
            continue
        mn = s.get("min_calls")
        rec = s.get("tool_calls_recursive")
        if mn and mn > 0 and rec and rec > 0:
            vals.append(min(mn / rec, 1.0))
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def _category_aggregates(samples: list[dict]) -> dict:
    total = len(samples)
    strict = sum(1 for s in samples if s.get("pass"))
    partial = sum(s.get("score", 0.0) for s in samples) / total if total else 0.0
    checks_passed = sum(s.get("checks_passed", 0) for s in samples)
    checks_total = sum(s.get("checks_total", 0) for s in samples)
    eff, eff_n = _efficiency(samples)
    return {
        "strict": strict,
        "total": total,
        "partial": round(partial, 4),
        "efficiency": round(eff, 4) if eff is not None else None,
        "efficiency_n": eff_n,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "by_difficulty": _bucket_by_difficulty(samples),
        "samples": samples,
    }


def convert(scores: dict) -> dict:
    """Return a new ``scores`` dict in post-suspension shape."""
    out: dict = {}

    new_categories: dict[str, dict] = {}
    for cat, info in scores.get("categories", {}).items():
        if cat == SUSPENDED_CATEGORY:
            continue
        kept = [
            s for s in info.get("samples", [])
            if sample_id(s) not in SUSPENDED_IDS
        ]
        if not kept:
            continue
        new_categories[cat] = _category_aggregates(kept)

    flat = sorted(
        [s for c in new_categories.values() for s in c["samples"]],
        key=lambda s: sample_id(s) or 0,
    )

    total = len(flat)
    strict = sum(1 for s in flat if s.get("pass"))
    partial_sum = sum(s.get("score", 0.0) for s in flat)
    completed = [s for s in flat if s.get("completed")]
    total_completed = len(completed)
    strict_completed = sum(1 for s in completed if s.get("pass"))
    partial_completed_sum = sum(s.get("score", 0.0) for s in completed)
    eff, eff_n = _efficiency(flat)

    all_checks = sum(c["checks_total"] for c in new_categories.values())
    all_passed = sum(c["checks_passed"] for c in new_categories.values())

    out["strict"] = strict
    out["total"] = total
    out["partial"] = round(partial_sum / total, 4) if total else 0.0
    out["strict_completed"] = strict_completed
    out["total_completed"] = total_completed
    out["partial_completed"] = (
        round(partial_completed_sum / total_completed, 4)
        if total_completed else 0.0
    )
    out["efficiency"] = round(eff, 4) if eff is not None else None
    out["efficiency_n"] = eff_n
    out["timed_out"] = total - total_completed

    if "context_overflow" in scores:
        out["context_overflow"] = scores["context_overflow"]

    out["checks_passed"] = all_passed
    out["checks_total"] = all_checks
    out["samples"] = flat
    out["categories"] = new_categories

    if "run" in scores:
        out["run"] = scores["run"]

    return out


def _format_delta(before: dict, after: dict) -> str:
    return (
        f"total {before.get('total')}->{after['total']}  "
        f"strict {before.get('strict')}->{after['strict']}  "
        f"partial {before.get('partial')}->{after['partial']}  "
        f"cats {len(before.get('categories', {}))}->{len(after['categories'])}"
    )


def process(
    path: Path,
    *,
    dry_run: bool,
    backup: bool,
    since: datetime | None,
) -> str:
    """Process a single scores.json. Returns a human-readable status string."""
    if since is not None:
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except FileNotFoundError:
            return f"[MISSING]   {path}"
        if mtime < since:
            return f"[SKIP pre-fix mtime={mtime:%Y-%m-%d %H:%M}] {path}"

    try:
        scores = json.loads(path.read_text())
    except Exception as exc:
        return f"[ERROR read]  {path}: {exc}"

    if is_already_converted(scores):
        return f"[SKIP done] {path}"

    try:
        new_scores = convert(scores)
    except Exception as exc:
        return f"[ERROR convert]  {path}: {exc}"

    delta = _format_delta(scores, new_scores)

    if dry_run:
        return f"[DRY]       {path}  {delta}"

    if backup:
        backup_path = path.with_name(path.name + BACKUP_SUFFIX)
        if not backup_path.exists():
            shutil.copy2(path, backup_path)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(new_scores, indent=2))
    tmp.replace(path)
    return f"[CONVERT]   {path}  {delta}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Drop suspended sample ids from legacy scores.json files "
                    "and recompute aggregates.")
    p.add_argument(
        "paths", nargs="*", type=Path,
        help="Specific scores.json files to convert. "
             "If omitted, walks --results-root/**/scores.json.")
    p.add_argument(
        "--results-root", type=Path, default=DEFAULT_RESULTS_ROOT,
        help=f"Root directory to walk for scores.json when no positional "
             f"paths are given. Default: {DEFAULT_RESULTS_ROOT}")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print what would change without writing anything.")
    p.add_argument(
        "--no-backup", action="store_true",
        help="Skip the .pre-v0.5.bak backup before overwriting.")
    p.add_argument(
        "--since", type=str, default=None,
        help="Only convert scores.json files with mtime >= this date "
             "(YYYY-MM-DD[ HH:MM]). Default: 2026-04-29 12:00 (latest "
             "grader fix). Use --all-runs to bypass entirely.")
    p.add_argument(
        "--all-runs", action="store_true",
        help="Bypass the --since cutoff and process every match.")
    return p.parse_args()


def _resolve_since(args: argparse.Namespace) -> datetime | None:
    if args.all_runs:
        return None
    if args.since:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(args.since, fmt)
            except ValueError:
                pass
        sys.exit(f"could not parse --since={args.since!r}; "
                 "expected YYYY-MM-DD or 'YYYY-MM-DD HH:MM'")
    return DEFAULT_SINCE


def _collect_paths(args: argparse.Namespace) -> list[Path]:
    if args.paths:
        return [p.resolve() for p in args.paths]
    root = args.results_root.resolve()
    if not root.exists():
        sys.exit(f"--results-root does not exist: {root}")
    return sorted(root.glob(SCORES_GLOB))


def main() -> int:
    args = parse_args()
    since = _resolve_since(args)
    paths = _collect_paths(args)

    if not paths:
        print("no scores.json files found")
        return 0

    backup = not args.no_backup
    converted = 0
    skipped = 0
    errors = 0
    for path in paths:
        line = process(
            path,
            dry_run=args.dry_run,
            backup=backup,
            since=since,
        )
        print(line)
        if line.startswith("[CONVERT]") or line.startswith("[DRY]"):
            converted += 1
        elif line.startswith("[ERROR"):
            errors += 1
        else:
            skipped += 1

    verb = "would-convert" if args.dry_run else "converted"
    print(
        f"\nsummary: {verb}={converted}  skipped={skipped}  errors={errors}  "
        f"total={len(paths)}"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
