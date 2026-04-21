#!/usr/bin/env python3
"""
Submit samples from data/samples_v0.jsonl (or data/samples_v1.jsonl when
`--version v1`) to the opencode CLI and save traces to runs/. A single
invocation targets exactly one version.

Each invocation writes to runs/{version}/{model_slug}/{timestamp}/ with:
    meta.json
    {id:03d}_{name}.jsonl       raw opencode trace
    projects/{id:03d}/          post-run workspace (copied from the canonical fixture)
    captures/ (with --proxy)    proxy payloads moved from the staging dir

The canonical projects/ tree is read-only at runtime.

Usage:
    python run.py                    # run all v0 samples (default)
    python run.py --version v1       # run all v1 samples (all repos)
    python run.py --id 1             # run one sample (within selected version)
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
    project_dir, run_project_name, trace_name,
    v1_repos, v1_repo_pin,
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
    src = project_dir(sample)

    if not src.is_dir():
        rel = src.relative_to(ROOT) if src.is_absolute() else src
        print(f"  SKIP #{sid} {name}: {rel}/ not found", flush=True)
        return None

    cwd = run_dir / "projects" / run_project_name(sample)
    if cwd.exists():
        shutil.rmtree(cwd)
    cwd.parent.mkdir(parents=True, exist_ok=True)
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

    stem = trace_name(sample)
    out = run_dir / f"{stem}.jsonl"
    out.write_text(stdout)

    if stderr.strip():
        (run_dir / f"{stem}.err").write_text(stderr)

    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    tools = sum(1 for l in lines if '"tool_use"' in l)
    print(f"{header}\n         {len(lines)} events, {tools} tool calls", flush=True)

    return out


def _move_captures(run_dir, cap_src, existing):
    """Move all new captures from staging into run_dir/captures/."""
    dst = run_dir / "captures"
    dst.mkdir(parents=True, exist_ok=True)
    moved = 0
    for f in sorted(cap_src.glob("*.json")):
        if f in existing:
            continue
        shutil.move(str(f), str(dst / f.name))
        moved += 1
    if moved:
        print(f"\nMoved {moved} capture(s) to {dst}/")


def _check_v1_pins(samples):
    """Preflight: for each distinct v1 repo in the selected samples, verify the
    submodule is checked out at the SHA declared in data/v1_repos.json. Aborts
    with an actionable hint on mismatch.
    """
    v1_samples = [s for s in samples if s.get("version") == "v1"]
    if not v1_samples:
        return
    repos_used = sorted({s["repo"] for s in v1_samples if s.get("repo")})
    repos = v1_repos()
    for repo in repos_used:
        entry = repos.get(repo)
        if not entry:
            print(f"ERROR: v1 sample references unknown repo {repo!r}; "
                  f"declare it in data/v1_repos.json")
            sys.exit(1)
        sub_path = ROOT / entry["submodule_path"]
        if not (sub_path / ".git").exists() and not (sub_path.is_dir() and any(sub_path.iterdir())):
            print(f"ERROR: submodule {entry['submodule_path']!r} not initialized\n"
                  f"  Fix: git submodule update --init {entry['submodule_path']}")
            sys.exit(1)
        try:
            got = subprocess.run(
                ["git", "-C", str(sub_path), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5, check=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as e:
            print(f"ERROR: could not read submodule HEAD for {repo!r}: {e}")
            sys.exit(1)
        want = entry["pin"]
        if got != want:
            print(f"ERROR: submodule pin drift for {repo!r}\n"
                  f"  declared (data/v1_repos.json): {want}\n"
                  f"  checked-out HEAD:              {got}\n"
                  f"  Fix: cd {entry['submodule_path']} && git fetch && git checkout {want}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Run specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Run all samples in a category")
    parser.add_argument(
        "--version",
        choices=["v0", "v1"],
        default="v0",
        help="Benchmark version to run. A single run targets exactly one "
             "version (default: v0). Run v1 separately with --version v1.",
    )
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
             "New files are moved to runs/{version}/{slug}/{timestamp}/captures/ "
             "after the run. Defaults to captures/ at the repo root.",
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

    _check_v1_pins(samples)

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
    run_dir = RUNS / args.version / slug / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "projects").mkdir(exist_ok=True)

    provider = args.proxy_provider
    if args.proxy and not provider:
        provider = args.model.split("/")[0] if args.model else "nvidia"

    v1_repos_used = sorted({s["repo"] for s in samples if s.get("version") == "v1" and s.get("repo")})
    meta = {
        "model": args.model,
        "model_slug": slug,
        "date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp": timestamp,
        "timeout": args.timeout,
        "samples": [s["id"] for s in samples],
        "categories": sorted(set(s["category"] for s in samples)),
        "version": args.version,
        "v1_repo_pins": {r: v1_repo_pin(r) for r in v1_repos_used},
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
        _move_captures(run_dir, cap_src, existing)

    print(f"\nDone. {ran} ran, {skipped} skipped")
    print(f"Run in {run_dir}/")


if __name__ == "__main__":
    main()
