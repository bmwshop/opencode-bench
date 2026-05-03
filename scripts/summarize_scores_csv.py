#!/usr/bin/env python3
"""
Summarize opencode-bench scores.json runs into the compact model CSV format.

By default this script only considers scores.json files whose filesystem mtime
is today in the local timezone. Pass --date, --since, or --all to choose a
different date scope.

Examples
--------
    python3 scripts/summarize_scores_csv.py --today
    python3 scripts/summarize_scores_csv.py --all --latest-only
    python3 scripts/summarize_scores_csv.py --date 2026-04-30 --model Qwen3-32B
    python3 scripts/summarize_scores_csv.py --date 2026-04-30 --group-by run \
        --output analysis/model_run_summary_20260430_runs.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


DEFAULT_RESULTS_ROOT = Path(
    "/lustre/fsw/portfolios/llmservice/users/drekesh/opencode-bench-results"
)
DEFAULT_OUTPUT = Path("summary.csv")

HEADER = [
    "model",
    "run_n",
    "never_completed",
    "pass@1_avg",
    "pass@1_std",
    "pass@n",
    "edit_pass@1",
    "edit_pass@n",
    "loc_pass@1",
    "loc_pass@n",
    "review_pass@1",
    "review_pass@n",
    "orch_pass@1",
    "orch_pass@n",
    "skill_pass@1",
    "skill_pass@n",
    "restriction_pass@1",
    "restriction_pass@n",
    "timed_out_avg",
    "context_overflow_avg",
]

EXPECTED_HEADER = (
    "model,run_n,never_completed,pass@1_avg,pass@1_std,pass@n,"
    "edit_pass@1,edit_pass@n,loc_pass@1,loc_pass@n,"
    "review_pass@1,review_pass@n,orch_pass@1,orch_pass@n,skill_pass@1,"
    "skill_pass@n,restriction_pass@1,restriction_pass@n,timed_out_avg,"
    "context_overflow_avg"
)

CATEGORY_COLUMNS = [
    ("code_editing", "edit"),
    ("code_localization", "loc"),
    ("code_review", "review"),
    ("orchestration", "orch"),
    ("skill", "skill"),
    ("tool_restriction", "restriction"),
]

SAMPLE_ID_RE = re.compile(r"#(\d+)")
PARALLEL_COPY_SUFFIX_RE = re.compile(r"-\d{2,}$")


@dataclass(frozen=True)
class SampleResult:
    sample_id: str
    passed: bool
    completed: bool


@dataclass(frozen=True)
class RunResult:
    path: Path
    family: str
    relative_parent: str
    mtime: datetime
    samples: list[SampleResult]
    categories: dict[str, list[SampleResult]]
    context_overflow_count: int | None

    @property
    def incomplete_count(self) -> int:
        return sum(1 for sample in self.samples if not sample.completed)

    @property
    def strict_rate(self) -> float:
        return rate(sum(1 for sample in self.samples if sample.passed), len(self.samples))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize opencode-bench scores.json files into the simplified "
            "per-family or per-run CSV."
        )
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=DEFAULT_RESULTS_ROOT,
        help=f"Root containing result families. Default: {DEFAULT_RESULTS_ROOT}",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help=(
            "Substring or regex filter over the family/run path. May be passed "
            "multiple times; matches are ORed."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all discovered result files unless --date/--since/--today is set.",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Only include scores.json files modified today in the local timezone.",
    )
    parser.add_argument(
        "--date",
        type=parse_date,
        help="Only include scores.json files modified on this local date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--since",
        type=parse_date,
        help="Only include scores.json files modified on or after this local date.",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Keep only the latest selected scores.json per top-level result family.",
    )
    parser.add_argument(
        "--group-by",
        choices=("family", "run"),
        default="family",
        help="Group rows by top-level family or by individual run path. Default: family.",
    )
    parser.add_argument(
        "--no-merge-parallel-jobs",
        dest="merge_parallel_jobs",
        action="store_false",
        default=True,
        help=(
            "Do not merge result families with run_cluster.py parallel-copy "
            "suffixes like '-00' or '-001' when grouping by family."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "CSV output path. Default: ./summary.csv relative to the current "
            "working directory."
        ),
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Write the CSV file without also printing it to stdout.",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print the CSV to stdout without writing a file.",
    )
    args = parser.parse_args()

    explicit_date_filters = sum(
        1 for value in (args.today, args.date is not None, args.since is not None) if value
    )
    if explicit_date_filters > 1:
        parser.error("Use only one of --today, --date, or --since.")
    if args.stdout_only and args.output is not None:
        parser.error("--stdout-only cannot be used with --output.")
    if args.stdout_only and args.no_print:
        parser.error("--stdout-only cannot be used with --no-print.")

    return args


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected YYYY-MM-DD date, got {value!r}"
        ) from exc


def main() -> int:
    if ",".join(HEADER) != EXPECTED_HEADER:
        raise AssertionError("CSV header constant does not match the required format")

    args = parse_args()
    date_filter = selected_date_filter(args)
    paths = discover_scores(args.results_root)
    paths = [
        path
        for path in paths
        if matches_date(path, date_filter) and matches_model_filter(path, args)
    ]
    if args.latest_only:
        paths = latest_per_family(paths, args.results_root)

    runs = load_runs(paths, args.results_root)
    if not runs:
        print("No matching scores.json files found.", file=sys.stderr)
        return 1

    rows = summarize_runs(runs, args.group_by, args.merge_parallel_jobs)
    emit_csv(render_csv(rows), args)
    return 0


def selected_date_filter(args: argparse.Namespace) -> tuple[str, date | None]:
    if args.today:
        return ("date", date.today())
    if args.date is not None:
        return ("date", args.date)
    if args.since is not None:
        return ("since", args.since)
    if args.all:
        return ("all", None)
    return ("date", date.today())


def discover_scores(results_root: Path) -> list[Path]:
    return sorted(
        (path for path in results_root.glob("**/scores.json") if path.is_file()),
        key=lambda path: path.as_posix(),
    )


def matches_date(path: Path, date_filter: tuple[str, date | None]) -> bool:
    mode, target = date_filter
    if mode == "all":
        return True
    path_date = datetime.fromtimestamp(path.stat().st_mtime).date()
    if mode == "date":
        return path_date == target
    if mode == "since":
        return path_date >= target
    raise ValueError(f"unknown date filter mode: {mode}")


def matches_model_filter(path: Path, args: argparse.Namespace) -> bool:
    if not args.model:
        return True
    search_text = model_search_text(path, args.results_root)
    return any(pattern_matches(pattern, search_text) for pattern in args.model)


def model_search_text(path: Path, results_root: Path) -> str:
    relative_parent = safe_relative(path.parent, results_root).as_posix()
    family = family_name(path, results_root)
    return f"{family}\n{relative_parent}"


def pattern_matches(pattern: str, text: str) -> bool:
    if pattern in text:
        return True
    try:
        return re.search(pattern, text) is not None
    except re.error:
        return False


def latest_per_family(paths: Iterable[Path], results_root: Path) -> list[Path]:
    latest: dict[str, Path] = {}
    for path in paths:
        family = family_name(path, results_root)
        current = latest.get(family)
        if current is None or path.stat().st_mtime > current.stat().st_mtime:
            latest[family] = path
    return sorted(latest.values(), key=lambda path: path.as_posix())


def load_runs(paths: Iterable[Path], results_root: Path) -> list[RunResult]:
    runs: list[RunResult] = []
    for path in paths:
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: skipping unreadable scores file {path}: {exc}", file=sys.stderr)
            continue

        relative_parent = safe_relative(path.parent, results_root).as_posix()
        runs.append(
            RunResult(
                path=path,
                family=family_name(path, results_root),
                relative_parent=relative_parent,
                mtime=datetime.fromtimestamp(path.stat().st_mtime),
                samples=parse_samples(payload.get("samples", [])),
                categories=parse_categories(payload.get("categories", {})),
                context_overflow_count=parse_context_overflow_count(payload),
            )
        )
    return runs


def family_name(path: Path, results_root: Path) -> str:
    relative = safe_relative(path, results_root)
    return no_space_identifier(relative.parts[0] if relative.parts else path.parent.name)


def safe_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def parse_samples(raw_samples: Any) -> list[SampleResult]:
    if not isinstance(raw_samples, list):
        return []
    return [parse_sample(sample) for sample in raw_samples if isinstance(sample, dict)]


def parse_categories(raw_categories: Any) -> dict[str, list[SampleResult]]:
    if not isinstance(raw_categories, dict):
        return {}
    parsed: dict[str, list[SampleResult]] = {}
    for category, payload in raw_categories.items():
        if not isinstance(payload, dict):
            continue
        parsed[category] = parse_samples(payload.get("samples", []))
    return parsed


def parse_sample(sample: dict[str, Any]) -> SampleResult:
    label = str(sample.get("label", ""))
    return SampleResult(
        sample_id=sample_id(label),
        passed=bool(sample.get("pass", False)),
        completed=sample.get("completed", True) is not False,
    )


def parse_context_overflow_count(payload: dict[str, Any]) -> int | None:
    aggregate = payload.get("context_overflow")
    if isinstance(aggregate, dict) and "samples_flagged" in aggregate:
        count = numeric_count(aggregate.get("samples_flagged"))
        if count is not None:
            return count

    sample_count = context_overflow_count_from_samples(payload.get("samples", []))
    if sample_count is not None:
        return sample_count

    raw_categories = payload.get("categories", {})
    if not isinstance(raw_categories, dict):
        return None

    saw_context_overflow = False
    total = 0
    for category_payload in raw_categories.values():
        if not isinstance(category_payload, dict):
            continue
        category_count = context_overflow_count_from_samples(
            category_payload.get("samples", [])
        )
        if category_count is not None:
            saw_context_overflow = True
            total += category_count
    return total if saw_context_overflow else None


def numeric_count(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def context_overflow_count_from_samples(raw_samples: Any) -> int | None:
    if not isinstance(raw_samples, list):
        return None

    saw_context_overflow = False
    total = 0
    for sample in raw_samples:
        if not isinstance(sample, dict) or "context_overflow" not in sample:
            continue
        saw_context_overflow = True
        if sample.get("context_overflow") is True:
            total += 1
    return total if saw_context_overflow else None


def sample_id(label: str) -> str:
    match = SAMPLE_ID_RE.search(label)
    return match.group(1) if match else label.strip()


def summarize_runs(
    runs: list[RunResult], group_by: str, merge_parallel_jobs: bool
) -> list[dict[str, str]]:
    groups: dict[str, list[RunResult]] = {}
    for run in runs:
        key = group_key(run, group_by, merge_parallel_jobs)
        groups.setdefault(key, []).append(run)

    return [
        summarize_group(model, sorted(group, key=lambda run: run.path.as_posix()))
        for model, group in sorted(groups.items())
    ]


def group_key(run: RunResult, group_by: str, merge_parallel_jobs: bool) -> str:
    if group_by == "family":
        return family_group_name(run.family, merge_parallel_jobs)
    return no_space_identifier(run.relative_parent)


def family_group_name(family: str, merge_parallel_jobs: bool) -> str:
    if not merge_parallel_jobs:
        return family
    return PARALLEL_COPY_SUFFIX_RE.sub("", family)


def summarize_group(model: str, runs: list[RunResult]) -> dict[str, str]:
    strict_rates = [run.strict_rate for run in runs]
    row = {
        "model": model,
        "run_n": str(len(runs)),
        "never_completed": str(never_completed_count(runs)),
        "pass@1_avg": format_percent(mean(strict_rates)),
        "pass@1_std": format_percent(sample_std(strict_rates)),
        "pass@n": format_percent(pass_n(sample for run in runs for sample in run.samples)),
    }

    for category, prefix in CATEGORY_COLUMNS:
        category_rates = [
            rate(sum(1 for sample in samples if sample.passed), len(samples))
            for samples in (run.categories.get(category, []) for run in runs)
        ]
        category_samples = (
            sample
            for run in runs
            for sample in run.categories.get(category, [])
        )
        row[f"{prefix}_pass@1"] = format_percent(mean(category_rates))
        row[f"{prefix}_pass@n"] = format_percent(pass_n(category_samples))

    row["timed_out_avg"] = format_count_avg(mean(run.incomplete_count for run in runs))
    # Mixed old/new selections average only runs that expose the new metadata;
    # all-legacy groups remain explicitly marked as unavailable.
    context_overflow_counts = [
        run.context_overflow_count
        for run in runs
        if run.context_overflow_count is not None
    ]
    row["context_overflow_avg"] = (
        format_count_avg(mean(context_overflow_counts))
        if context_overflow_counts
        else "n/a"
    )
    return row


def never_completed_count(runs: list[RunResult]) -> int:
    by_sample: dict[str, list[bool]] = {}
    for run in runs:
        completed_by_id = {sample.sample_id: sample.completed for sample in run.samples}
        for sample_id_value, completed in completed_by_id.items():
            by_sample.setdefault(sample_id_value, []).append(completed)
    return sum(
        1
        for completions in by_sample.values()
        if len(completions) == len(runs) and not any(completions)
    )


def pass_n(samples: Iterable[SampleResult]) -> float:
    passed_by_id: dict[str, bool] = {}
    for sample in samples:
        passed_by_id[sample.sample_id] = passed_by_id.get(sample.sample_id, False) or sample.passed
    if not passed_by_id:
        return 0.0
    return sum(1 for passed in passed_by_id.values() if passed) / len(passed_by_id)


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def mean(values: Iterable[float | int]) -> float:
    values_list = list(values)
    return statistics.fmean(values_list) if values_list else 0.0


def sample_std(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_count_avg(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}"


def no_space_identifier(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip())


def render_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HEADER, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def emit_csv(csv_content: str, args: argparse.Namespace) -> None:
    if args.stdout_only:
        sys.stdout.write(csv_content)
        return

    write_csv(csv_content, args.output or DEFAULT_OUTPUT)
    if not args.no_print:
        sys.stdout.write(csv_content)


def write_csv(csv_content: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        handle.write(csv_content)


if __name__ == "__main__":
    raise SystemExit(main())
