#!/usr/bin/env python3
"""
Evaluate opencode benchmark traces against checks defined in samples.jsonl.

Usage:
    python eval.py                # evaluate all
    python eval.py --id 1         # evaluate one sample
    python eval.py --id 1 --id 2  # evaluate multiple samples
    python eval.py --category tool_schema
    python eval.py --category tool_schema --category subagent
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Evaluate specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Evaluate all samples in a category")
    args = parser.parse_args()

    load_evaluators()

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    results = [evaluate(s) for s in samples]

    by_cat = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    total = len(results)
    sum_strict = 0
    sum_partial = 0.0

    for cat, rs in sorted(by_cat.items()):
        cat_strict = sum(1 for r in rs if r.ok)
        cat_partial = sum(r.score for r in rs) / len(rs) if rs else 0.0
        print(f"\n{'='*60}")
        print(f"  {cat}  (strict {cat_strict}/{len(rs)}, partial {cat_partial:.0%})")
        print(f"{'='*60}")
        for r in rs:
            icon = "PASS" if r.ok else "FAIL"
            print(f"  [{icon}] {r.label} ({r.score:.0%})")
            for msg in r.failed:
                print(f"         - {msg}")
        sum_strict += cat_strict
        sum_partial += sum(r.score for r in rs)

    avg_strict = sum_strict / total if total else 0.0
    avg_partial = sum_partial / total if total else 0.0
    print(f"\n{'='*60}")
    if total:
        print(f"  Strict score:  {sum_strict}/{total} samples fully passed ({avg_strict:.0%})")
        print(f"  Partial score: {avg_partial:.1%} average across all samples")
    else:
        print("  No results.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
