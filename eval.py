#!/usr/bin/env python3
"""
Evaluate opencode benchmark traces against checks defined in samples.jsonl.

Usage:
    python eval.py                        # evaluate all
    python eval.py --id 1                 # evaluate one sample
    python eval.py --id 1 --id 2          # evaluate multiple samples
    python eval.py --category tool_schema
    python eval.py --format json          # machine-readable output
    python eval.py --output scores.json --format json   # write to file
    python eval.py --output scores.txt    # write text to file
"""

import json
import sys
import argparse
import importlib
import pkgutil
from dataclasses import dataclass, field

import evaluators
from common import PROJECTS, RESULTS, load


def load_evaluators():
    for pkg in pkgutil.walk_packages(evaluators.__path__, evaluators.__name__ + "."):
        importlib.import_module(pkg.name)


@dataclass
class Result:
    label: str
    category: str
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)

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


def evaluate(sample):
    sid = sample["id"]
    name = sample.get("name", str(sid))
    label = f"#{sid} {name}"
    trace = RESULTS / f"{sid}_{name}.jsonl"

    if not trace.exists():
        return Result(label, sample["category"], failed=["trace not found"])

    tools, texts = extract(trace)
    if not tools and not texts:
        return Result(label, sample["category"], failed=["empty trace"])

    project = PROJECTS / sample.get("project", "default")
    result = Result(label, sample["category"])
    for chk in sample.get("checks", []):
        fn = evaluators.get(chk["type"])
        if not fn:
            result.failed.append(f"unknown check type: {chk['type']!r}")
            continue
        chk["_project_dir"] = str(project)
        ok, reason = fn(tools, texts, chk)
        desc = chk.get("description", chk["type"])
        if ok:
            result.passed.append(desc)
        else:
            result.failed.append(f"{desc}: {reason}" if reason and reason != desc else desc)

    return result


def _checks(r):
    return len(r.passed) + len(r.failed)


def build(results):
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
                "checks_passed": len(r.passed),
                "checks_total": _checks(r),
                "passed": r.passed,
                "failed": r.failed,
            })
        categories[cat] = {
            "strict": cat_strict,
            "total": len(rs),
            "partial": round(cat_partial, 4),
            "checks_passed": cat_passed,
            "checks_total": cat_checks,
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

    return {
        "strict": sum_strict,
        "total": total,
        "partial": round(sum_partial / total, 4) if total else 0.0,
        "checks_passed": all_passed,
        "checks_total": all_checks,
        "samples": flat,
        "categories": categories,
    }


def format_text(data):
    lines = []
    for cat, info in sorted(data["categories"].items()):
        lines.append(f"\n{'='*60}")
        lines.append(f"  {cat}  (strict {info['strict']}/{info['total']}, "
                      f"partial {info['partial']:.0%}, "
                      f"checks {info['checks_passed']}/{info['checks_total']})")
        lines.append(f"{'='*60}")
        for s in info["samples"]:
            icon = "PASS" if s["pass"] else "FAIL"
            lines.append(f"  [{icon}] {s['label']} "
                         f"({s['checks_passed']}/{s['checks_total']} checks, {s['score']:.0%})")
            for msg in s["failed"]:
                lines.append(f"         - {msg}")

    lines.append(f"\n{'='*60}")
    if data["total"]:
        lines.append(f"  Strict score:  {data['strict']}/{data['total']} samples fully passed "
                      f"({data['strict']/data['total']:.0%})")
        lines.append(f"  Partial score: {data['partial']:.1%} average across all samples")
        lines.append(f"  Checks:        {data['checks_passed']}/{data['checks_total']} total checks passed")
    else:
        lines.append("  No results.")
    lines.append(f"{'='*60}\n")
    return "\n".join(lines)


def format_json(data):
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Evaluate specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Evaluate all samples in a category")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Write results to file (in addition to stdout)")
    args = parser.parse_args()

    load_evaluators()

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    results = [evaluate(s) for s in samples]
    data = build(results)
    output = format_json(data) if args.format == "json" else format_text(data)
    print(output)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output + "\n")
        print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
