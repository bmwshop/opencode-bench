#!/usr/bin/env python3
"""
Evaluate opencode benchmark traces against the checks defined in
data/samples_v0.jsonl and data/samples_v1.jsonl. The run's version is
auto-detected from its meta.json; override with --version.

Usage:
    python eval.py                        # evaluate latest run (auto-detects version)
    python eval.py --version v1           # force v1 scope
    python eval.py --model nvidia/nemotron          # latest run for model
    python eval.py --model nvidia/nemotron --run 2026-04-12T18-30-00
    python eval.py --list                 # show all available runs
    python eval.py --id 1                 # evaluate one sample
    python eval.py --id 1 --id 2          # evaluate multiple samples
    python eval.py --category tool_schema
    python eval.py --format json          # machine-readable output
    python eval.py --output scores.json --format json   # write to file
    python eval.py --output scores.txt    # write text to file
"""

import json
import shutil
import sys
import argparse
import importlib
import pkgutil
from dataclasses import dataclass, field

import evaluators
from evaluators._recursive import _collect_recursive_tools, _real_tools
from common import (
    PROJECTS, RUNS, SCHEMAS_PATH,
    load, resolve_run, list_runs, model_slug, version_of,
    opencode_rev_label, schema_meta, compare_opencode,
    project_dir, run_project_name, trace_name,
)


def load_evaluators():
    for pkg in pkgutil.walk_packages(evaluators.__path__, evaluators.__name__ + "."):
        importlib.import_module(pkg.name)


def refresh_schemas():
    """Re-extract data/tool_schemas.json from the (current) opencode install.

    Honors $OPENCODE_BIN / $OPENCODE_CWD so you can target a source build:
        OPENCODE_BIN="bun run src/index.ts" \\
            OPENCODE_CWD=/path/to/opencode/packages/opencode \\
            python eval.py --refresh-schemas
    """
    from scripts.extract_schemas import extract
    out = extract()
    print(
        f"Refreshed tool schemas: opencode {out['opencode_version']} "
        f"({len(out['tools'])} tools) -> {SCHEMAS_PATH}"
    )


def schemas_banner():
    sm = schema_meta()
    if sm is None:
        return "Tool schemas: (not extracted; run with --refresh-schemas)"
    return (
        f"Tool schemas: opencode {opencode_rev_label(sm)} "
        f"({sm['tools']} tools, extracted {sm['extracted_at']})"
    )


TAG = {"match": "MATCH", "match-version": "MATCH: version", "mismatch": "MISMATCH", "unknown": "WARN"}


def compare_banner(run_oc):
    """Compare run.py's opencode (from meta.json) vs the schemas' opencode."""
    sm = schema_meta()
    if not run_oc or not sm:
        return None
    status, detail = compare_opencode(run_oc, sm)
    line = (
        f"Runtime opencode: {opencode_rev_label(run_oc)}  "
        f"vs  schemas: {opencode_rev_label(sm)}"
    )
    return f"{line}  [{TAG[status]}: {detail}]"


@dataclass
class Result:
    label: str
    category: str
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    completed: bool = True
    min_calls: int | None = None
    tool_calls_recursive: int | None = None
    difficulty: str | None = None

    @property
    def ok(self):
        return len(self.failed) == 0

    @property
    def score(self):
        total = len(self.passed) + len(self.failed)
        return len(self.passed) / total if total else 0.0


def extract(path):
    tools = []
    texts = []
    if not path.exists():
        return tools, texts
    step = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") == "step_start":
                step += 1
            if evt.get("type") == "tool_use":
                part = evt.get("part", {})
                state = part.get("state", {})
                tools.append({
                    "name": part.get("tool", ""),
                    "input": state.get("input", {}),
                    "output": state.get("output", ""),
                    "step": step,
                })
            if evt.get("type") == "text":
                texts.append(evt.get("part", {}).get("text", ""))
    return tools, texts


def evaluate(sample, run_dir):
    sid = sample["id"]
    name = sample.get("name", str(sid))
    label = f"#{sid} {name}"

    run_dir = run_dir.resolve()
    trace = run_dir / f"{trace_name(sample)}.jsonl"
    if not trace.exists():
        return Result(label, sample["category"], failed=["trace not found"],
                      completed=False, difficulty=sample.get("difficulty"))

    tools, texts = extract(trace)
    if not tools and not texts:
        return Result(label, sample["category"], failed=["empty trace"],
                      completed=False, difficulty=sample.get("difficulty"))

    project = run_dir / "projects" / run_project_name(sample)
    if not project.is_dir():
        try:
            project = project_dir(sample)
        except (ValueError, AssertionError):
            pass
    result = Result(label, sample["category"])
    result.min_calls = sample.get("min_calls")
    result.tool_calls_recursive = len(_real_tools(_collect_recursive_tools(trace)))
    result.difficulty = sample.get("difficulty")
    for chk in sample.get("checks", []):
        fn = evaluators.get(chk["type"])
        if not fn:
            result.failed.append(f"unknown check type: {chk['type']!r}")
            continue
        chk["_project_dir"] = str(project)
        # Evaluators that need the trace path so they can walk
        # `{stem}.subagent-*.json` sidecars: every `_recursive` wrapper, the
        # recurse-by-default `call_schema_valid`, and the 2026-04 orchestration
        # evaluators (`tool_call_count`, `parallel_dispatch_count`,
        # `tool_call_sequence`) which accept `trace_path=None` and switch to
        # recursive aggregation when it's supplied. Strict evaluators take
        # 3 positional args and would reject a kwarg.
        TRACE_AWARE = {
            "call_schema_valid",
            "tool_call_count",
            "parallel_dispatch_count",
            "tool_call_sequence",
        }
        if chk["type"].endswith("_recursive") or chk["type"] in TRACE_AWARE:
            ok, reason = fn(tools, texts, chk, trace_path=trace)
        else:
            ok, reason = fn(tools, texts, chk)
        desc = chk.get("description", chk["type"])
        if ok:
            result.passed.append(desc)
        else:
            result.failed.append(f"{desc}: {reason}" if reason and reason != desc else desc)

    return result


def _checks(r):
    return len(r.passed) + len(r.failed)


_DIFFICULTY_ORDER = ["easy", "medium", "hard"]


def _bucket_by_difficulty(results):
    """Return {tier: {strict: int, total: int, partial: float}} over a list of
    Result objects. Only buckets tiers that have at least one sample. Samples
    without a `difficulty` attribute are placed under `None` and omitted from
    the returned mapping (so this is a no-op for legacy categories like
    `plan_mode`).
    """
    buckets: dict[str, list] = {}
    for r in results:
        if not r.difficulty:
            continue
        buckets.setdefault(r.difficulty, []).append(r)
    out: dict[str, dict] = {}
    for tier in _DIFFICULTY_ORDER:
        rs = buckets.get(tier)
        if not rs:
            continue
        total = len(rs)
        strict = sum(1 for r in rs if r.ok)
        partial = sum(r.score for r in rs) / total
        out[tier] = {
            "strict": strict,
            "total": total,
            "partial": round(partial, 4),
        }
    # Surface any unexpected tier values (future-proofing).
    for tier, rs in buckets.items():
        if tier in out or tier not in _DIFFICULTY_ORDER:
            if tier not in out:
                total = len(rs)
                strict = sum(1 for r in rs if r.ok)
                partial = sum(r.score for r in rs) / total
                out[tier] = {
                    "strict": strict,
                    "total": total,
                    "partial": round(partial, 4),
                }
    return out


def _efficiency(results):
    """Mean of min(min_calls / tool_calls_recursive, 1.0) over strict-passing
    samples with a declared min_calls > 0 and a positive observed recursive
    count. Returns (mean_in_[0,1] or None, n_contributing)."""
    vals = [
        min(r.min_calls / r.tool_calls_recursive, 1.0)
        for r in results
        if r.ok
        and r.min_calls and r.min_calls > 0
        and r.tool_calls_recursive and r.tool_calls_recursive > 0
    ]
    return (sum(vals) / len(vals) if vals else None), len(vals)


def build(results, meta=None):
    by_cat = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    total = len(results)
    sum_strict = 0
    sum_partial = 0.0
    categories = {}

    for cat, rs in sorted(by_cat.items()):
        cat_strict = sum(1 for r in rs if r.ok)
        cat_partial = sum(r.score for r in rs) / len(rs) if rs else 0.0
        cat_checks = sum(_checks(r) for r in rs)
        cat_passed = sum(len(r.passed) for r in rs)
        samples = []
        for r in rs:
            samples.append({
                "label": r.label,
                "pass": r.ok,
                "score": round(r.score, 4),
                "completed": r.completed,
                "checks_passed": len(r.passed),
                "checks_total": _checks(r),
                "passed": r.passed,
                "failed": r.failed,
                "min_calls": r.min_calls,
                "tool_calls_recursive": r.tool_calls_recursive,
                "difficulty": r.difficulty,
            })
        cat_eff, cat_eff_n = _efficiency(rs)
        categories[cat] = {
            "strict": cat_strict,
            "total": len(rs),
            "partial": round(cat_partial, 4),
            "efficiency": round(cat_eff, 4) if cat_eff is not None else None,
            "efficiency_n": cat_eff_n,
            "checks_passed": cat_passed,
            "checks_total": cat_checks,
            "by_difficulty": _bucket_by_difficulty(rs),
            "samples": samples,
        }
        sum_strict += cat_strict
        sum_partial += sum(r.score for r in rs)

    all_checks = sum(c["checks_total"] for c in categories.values())
    all_passed = sum(c["checks_passed"] for c in categories.values())

    flat = sorted(
        [s for c in categories.values() for s in c["samples"]],
        key=lambda s: int(s["label"].split()[0].lstrip("#")),
    )

    completed_results = [r for r in results if r.completed]
    total_completed = len(completed_results)
    strict_completed = sum(1 for r in completed_results if r.ok)
    partial_completed = (
        sum(r.score for r in completed_results) / total_completed
        if total_completed else 0.0
    )

    eff, eff_n = _efficiency(results)

    data = {
        "strict": sum_strict,
        "total": total,
        "partial": round(sum_partial / total, 4) if total else 0.0,
        "strict_completed": strict_completed,
        "total_completed": total_completed,
        "partial_completed": round(partial_completed, 4),
        "efficiency": round(eff, 4) if eff is not None else None,
        "efficiency_n": eff_n,
        "timed_out": total - total_completed,
        "checks_passed": all_passed,
        "checks_total": all_checks,
        "samples": flat,
        "categories": categories,
    }

    if meta:
        data["run"] = {
            "model": meta.get("model"),
            "date": meta.get("date"),
            "timestamp": meta.get("timestamp"),
            "model_slug": meta.get("model_slug"),
        }

    return data


def format_text(data):
    lines = []

    run_info = data.get("run")
    if run_info:
        model = run_info.get("model") or run_info.get("model_slug") or "unknown"
        date = run_info.get("date", "unknown")
        lines.append(f"  Run: {model}  ({date})")

    for cat, info in sorted(data["categories"].items()):
        lines.append(f"\n{'='*60}")
        eff_tok = (
            f", efficiency {info['efficiency']:.0%} (n={info['efficiency_n']})"
            if info.get("efficiency") is not None else ""
        )
        lines.append(f"  {cat}  (strict {info['strict']}/{info['total']}, "
                      f"partial {info['partial']:.0%}{eff_tok}, "
                      f"checks {info['checks_passed']}/{info['checks_total']})")
        by_diff = info.get("by_difficulty") or {}
        if by_diff:
            parts = [
                f"{tier} {b['strict']}/{b['total']} ({b['partial']:.0%})"
                for tier in ("easy", "medium", "hard") if (b := by_diff.get(tier))
            ]
            # Append any non-standard tiers to preserve forward-compat.
            for tier, b in by_diff.items():
                if tier not in ("easy", "medium", "hard"):
                    parts.append(f"{tier} {b['strict']}/{b['total']} ({b['partial']:.0%})")
            if parts:
                lines.append(f"    by difficulty: {', '.join(parts)}")
        lines.append(f"{'='*60}")
        for s in info["samples"]:
            icon = "PASS" if s["pass"] else "FAIL"
            diff_tag = f" [{s['difficulty']}]" if s.get("difficulty") else ""
            lines.append(f"  [{icon}] {s['label']}{diff_tag} "
                         f"({s['checks_passed']}/{s['checks_total']} checks, {s['score']:.0%})")
            for msg in s["failed"]:
                lines.append(f"         - {msg}")

    lines.append(f"\n{'='*60}")
    if data["total"]:
        lines.append(f"  Strict score:      {data['strict']}/{data['total']} samples fully passed "
                      f"({data['strict']/data['total']:.0%})")
        lines.append(f"  Partial score:     {data['partial']:.1%} average across all samples")
        if data.get("efficiency") is not None:
            lines.append(
                f"  Efficiency:        {data['efficiency']:.1%} across "
                f"{data['efficiency_n']} strict-passing sample(s) "
                f"(mean of min(min_calls / tool_calls_recursive, 1.0))"
            )
        tc = data.get("total_completed", data["total"])
        if tc and tc != data["total"]:
            sc = data["strict_completed"]
            pc = data["partial_completed"]
            to = data["timed_out"]
            lines.append(f"  Strict (done):     {sc}/{tc} passed of {tc} completed "
                          f"({sc/tc:.0%})")
            lines.append(f"  Partial (done):    {pc:.1%} average across completed samples")
            lines.append(f"  Timed out:         {to}")
        lines.append(f"  Checks:            {data['checks_passed']}/{data['checks_total']} total checks passed")
    else:
        lines.append("  No results.")
    lines.append(f"{'='*60}\n")
    return "\n".join(lines)


def format_json(data):
    return json.dumps(data, indent=2)


def print_list(model_filter=None, version=None):
    """Print available runs grouped by version + model."""
    slug_filter = model_slug(model_filter) if model_filter else None

    found = False
    current = None
    for v, ms, ts, meta in list_runs(version=version):
        if slug_filter and ms != slug_filter:
            continue
        header = (v, ms)
        if header != current:
            if current is not None:
                print()
            print(f"  [{v}] {ms}")
            current = header
        n = len(meta.get("samples", []))
        timeout = meta.get("timeout", "?")
        print(f"    {ts}  ({n} samples, {timeout}s timeout)")
        found = True

    if not found:
        print("No runs found.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Evaluate specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Evaluate all samples in a category")
    parser.add_argument(
        "--version",
        choices=["v0", "v1"],
        default=None,
        help="Benchmark version to evaluate. Defaults to the run's version "
             "from meta.json (a run targets exactly one version).",
    )
    parser.add_argument("--model", "-m", help="Model in provider/model format (selects latest run for model)")
    parser.add_argument("--run", help="Timestamp of a specific run (requires --model)")
    parser.add_argument("--list", action="store_true", help="List available runs and exit")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Write results to file (in addition to stdout)")
    parser.add_argument(
        "--refresh-schemas",
        action="store_true",
        help="Re-extract data/tool_schemas.json from opencode before evaluating "
             "(uses $OPENCODE_BIN / $OPENCODE_CWD if set).",
    )
    parser.add_argument(
        "--no-cleanup-projects",
        dest="cleanup_projects",
        action="store_false",
        default=True,
        help="Retain per-task project copies at run_dir/projects/{NNN}/ after "
             "evaluation. By default eval.py deletes them — saves disk but "
             "prevents future re-scoring (file-graded evaluators exec_assert, "
             "exec_function, and file_regex_disk read source files from the "
             "workspace). Pass this flag if you intend to re-score the run "
             "later (e.g. after a grader fix). Trace JSONL, subagent sidecars, "
             "captures/, scores.json, and meta.json are always kept regardless.",
    )
    args = parser.parse_args()

    if args.refresh_schemas:
        refresh_schemas()

    if args.list:
        print_list(args.model, version=args.version)
        return

    if args.run and not args.model:
        print("ERROR: --run requires --model to identify which model's run to use")
        sys.exit(1)

    run_dir = resolve_run(model=args.model, run=args.run, version=args.version)
    if not run_dir:
        where = f"version={args.version}" if args.version else "any version"
        if args.model:
            print(f"No runs found for model {args.model!r} ({where})")
        else:
            print(f"No runs found ({where}). Run benchmarks first with: python run.py")
        sys.exit(1)

    # run_dir is runs/{version}/{slug}/{ts}/ — lock args.version to it so
    # load() pulls samples from exactly the tier the run targeted.
    args.version = version_of(run_dir) or args.version

    meta_path = run_dir / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    model_label = meta.get("model") or run_dir.parent.name
    date_label = meta.get("date") or run_dir.name
    print(f"Evaluating: {model_label}  [{args.version}]  ({date_label})")
    print(f"Run dir:    {run_dir}")
    print(schemas_banner())
    cmp_line = compare_banner(meta.get("opencode"))
    if cmp_line:
        print(cmp_line)
    print()

    load_evaluators()

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    results = []
    cleaned = 0
    for s in samples:
        results.append(evaluate(s, run_dir))
        if args.cleanup_projects:
            pdir = run_dir / "projects" / run_project_name(s)
            if pdir.is_dir():
                shutil.rmtree(pdir, ignore_errors=True)
                cleaned += 1
    if args.cleanup_projects:
        projects_root = run_dir / "projects"
        removed_root = False
        if projects_root.is_dir() and not any(projects_root.iterdir()):
            try:
                projects_root.rmdir()
                removed_root = True
            except OSError:
                pass
        suffix = " (and removed empty projects/ root)" if removed_root else ""
        print(f"Cleaned {cleaned} project copy(ies) under {projects_root}/" + suffix)
    data = build(results, meta=meta)
    output = format_json(data) if args.format == "json" else format_text(data)
    print(output)

    scores_path = run_dir / "scores.json"
    scores_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Scores saved to {scores_path}")

    if args.output:
        with open(args.output, "w") as f:
            f.write(output + "\n")
        print(f"Results also written to {args.output}")


if __name__ == "__main__":
    main()
