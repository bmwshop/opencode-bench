#!/usr/bin/env python3
"""
Submit samples from samples.jsonl to opencode CLI and save traces to runs/.

Each invocation writes to runs/{model_slug}/{timestamp}/ with:
    meta.json
    {id}_{name}.jsonl           raw opencode trace
    projects/{id:03d}/          post-run workspace (copied from projects/{id:03d}/)
    captures/ (with --proxy)    proxy payloads moved from the staging dir

The canonical projects/ tree is read-only at runtime.

Usage:
    python run.py                    # run all samples
    python run.py --id 1             # run one sample
    python run.py --id 1 --id 2      # run multiple samples
    python run.py --category tool_schema
    python run.py --category tool_schema --category subagent
    python run.py --model provider/model-name
    python run.py --proxy http://localhost:4000/v1
    python run.py --proxy http://localhost:4000/v1 --capture-dir /tmp/sw
    python run.py --clean            # wipe runs/ first
    python run.py --timeout 120      # custom timeout
"""

import json
import subprocess
import shutil
import sys
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from common import (
    ROOT, PROJECTS, RUNS,
    model_slug, load,
    opencode_meta, opencode_rev_label, resolve_opencode_cmd,
    schema_meta, compare_opencode,
)

DEFAULT_TIMEOUT = 180
CAPTURE_STAGING = ROOT / "captures"


def _inject_proxy(cwd, provider, url):
    path = cwd / "opencode.json"
    cfg = json.loads(path.read_text()) if path.exists() else {}
    cfg.setdefault("provider", {}).setdefault(provider, {}).setdefault("options", {})["baseURL"] = url
    path.write_text(json.dumps(cfg, indent=2))


def run(sample, timeout, run_dir, model=None, proxy=None, provider=None):
    sid = sample["id"]
    name = sample.get("name", str(sid))
    src = PROJECTS / f"{sid:03d}"

    if not src.is_dir():
        print(f"  SKIP #{sid} {name}: projects/{sid:03d}/ not found", flush=True)
        return None

    cwd = run_dir / "projects" / f"{sid:03d}"
    if cwd.exists():
        shutil.rmtree(cwd)
    shutil.copytree(src, cwd)

    if proxy:
        _inject_proxy(cwd, provider, proxy)

    header = f"  RUN  #{sid:03d} {name}"
    start = time.time()

    argv, _, _ = resolve_opencode_cmd()
    try:
        proc = subprocess.Popen(
            [*argv, "run", "--format", "json"]
            + (["--model", model] if model else [])
            + (["--agent", sample["agent"]] if "agent" in sample else [])
            + [sample["prompt"]],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        elapsed = time.time() - start
        header += f"  ({elapsed:.0f}s)"
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        elapsed = time.time() - start
        header += f"  TIMEOUT ({elapsed:.0f}s)"
    except FileNotFoundError:
        print(f"  ERROR: opencode not found in PATH", flush=True)
        sys.exit(1)

    if "Model not found" in stderr or "Invalid model" in stderr:
        print(f"{header}\n  ERROR: {stderr.strip()}", flush=True)
        sys.exit(1)

    out = run_dir / f"{sid}_{name}.jsonl"
    out.write_text(stdout)

    if stderr.strip():
        (run_dir / f"{sid}_{name}.err").write_text(stderr)

    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    tools = sum(1 for l in lines if '"tool_use"' in l)
    print(f"{header}\n         {len(lines)} events, {tools} tool calls", flush=True)

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Run specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Run all samples in a category")
    parser.add_argument("--clean", action="store_true", help="Wipe runs/ first")
    parser.add_argument(
        "--model",
        "-m",
        default="nvidia/nvidia/nemotron-3-nano-30b-a3b",
        help="Model in provider/model format (default: nvidia/nvidia/nemotron-3-nano-30b-a3b)",
    )
    parser.add_argument(
        "--proxy",
        help="Proxy URL (e.g. http://localhost:4000/v1). "
             "Injects provider baseURL override into project configs.",
    )
    parser.add_argument(
        "--proxy-provider",
        default=None,
        help="Provider ID to route through proxy (default: inferred from --model)",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--workers",
        "-j",
        type=int,
        default=1,
        help="Number of samples to run in parallel (default: 1)",
    )
    parser.add_argument(
        "--capture-dir",
        default=None,
        help="Staging directory where switchyard writes captures. "
             "New files are moved to runs/{slug}/{timestamp}/captures/ after the run. "
             "Defaults to captures/ at the repo root.",
    )
    parser.add_argument(
        "--skip-schema-check",
        action="store_true",
        help="Skip the preflight that refuses to run when the opencode "
             "runtime doesn't match data/tool_schemas.json (only enforced "
             "when any sample uses call_schema_valid).",
    )
    args = parser.parse_args()

    if args.model and "/" not in args.model:
        print(f"ERROR: --model must be in provider/model format (got '{args.model}')")
        sys.exit(1)

    if args.workers < 1:
        print(f"ERROR: --workers must be >= 1 (got {args.workers})")
        sys.exit(1)

    if args.proxy and args.workers > 1:
        print(
            "WARNING: --proxy + --workers > 1: the stitch.py timestamp fallback "
            "for zero-tool-call samples has a 3s window and may misattribute "
            "captures. Tool-call samples are unaffected.\n"
        )

    if args.clean and RUNS.exists():
        shutil.rmtree(RUNS)
        print("Cleaned runs/\n")

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    oc_meta = opencode_meta()
    needs_schema = any(
        c.get("type") == "call_schema_valid"
        for s in samples for c in s.get("checks", [])
    )
    if needs_schema and not args.skip_schema_check:
        sch = schema_meta()
        if sch is None:
            print(
                "ERROR: samples use call_schema_valid but data/tool_schemas.json "
                "is missing.\n"
                "  Fix: python scripts/extract_schemas.py  (or --skip-schema-check)"
            )
            sys.exit(1)
        status, detail = compare_opencode(oc_meta, sch)
        if status not in ("match", "match-version"):
            runtime_lbl = opencode_rev_label(oc_meta)
            schema_lbl = opencode_rev_label(sch)
            print(
                f"ERROR: opencode runtime vs tool_schemas.json {status.upper()}:\n"
                f"  runtime: {runtime_lbl}\n"
                f"  schemas: {schema_lbl}\n"
                f"  detail:  {detail}\n"
                "  Fix: re-extract schemas against the runtime you intend to "
                "benchmark\n"
                "         python scripts/extract_schemas.py\n"
                "       or override via OPENCODE_BIN / OPENCODE_CWD, or pass "
                "--skip-schema-check."
            )
            sys.exit(1)

    now = datetime.now(timezone.utc)
    slug = model_slug(args.model)
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = RUNS / slug / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "projects").mkdir(exist_ok=True)

    provider = args.proxy_provider
    if args.proxy and not provider:
        provider = args.model.split("/")[0] if args.model else "nvidia"

    meta = {
        "model": args.model,
        "model_slug": slug,
        "date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp": timestamp,
        "timeout": args.timeout,
        "samples": [s["id"] for s in samples],
        "categories": sorted(set(s["category"] for s in samples)),
        "proxy": args.proxy,
        "argv": sys.argv,
        "opencode": oc_meta,
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"  opencode: {opencode_rev_label(oc_meta)}", flush=True)

    cap_src = Path(args.capture_dir) if args.capture_dir else CAPTURE_STAGING
    existing = set(cap_src.glob("*.json")) if cap_src.is_dir() else set()

    parts = []
    if args.model:
        parts.append(f"model={args.model}")
    if args.proxy:
        parts.append(f"proxy={args.proxy} ({provider})")
    if args.workers > 1:
        parts.append(f"workers={args.workers}")
    label = f"{', '.join(parts)}, " if parts else ""
    print(f"Running {len(samples)} sample(s) ({label}timeout={args.timeout}s)")
    print(f"Run dir: {run_dir}\n")

    ran = 0
    skipped = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [
            ex.submit(
                run, sample, args.timeout, run_dir,
                model=args.model, proxy=args.proxy, provider=provider,
            )
            for sample in samples
        ]
        for f in as_completed(futures):
            if f.result():
                ran += 1
            else:
                skipped += 1

    if cap_src.is_dir():
        cap_dst = run_dir / "captures"
        cap_dst.mkdir(parents=True, exist_ok=True)
        moved = 0
        for f in sorted(cap_src.glob("*.json")):
            if f not in existing:
                shutil.move(str(f), str(cap_dst / f.name))
                moved += 1
        if moved:
            print(f"\nMoved {moved} capture(s) to {cap_dst}/")

    print(f"\nDone. {ran} ran, {skipped} skipped")
    print(f"Run in {run_dir}/")


if __name__ == "__main__":
    main()
