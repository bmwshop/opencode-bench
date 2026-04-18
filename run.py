#!/usr/bin/env python3
"""
Submit samples from samples.jsonl to opencode CLI and save traces to results/.

Results are stored in results/{model_slug}/{timestamp}/ with a meta.json file.

Usage:
    python run.py                    # run all samples
    python run.py --id 1             # run one sample
    python run.py --id 1 --id 2      # run multiple samples
    python run.py --category tool_schema
    python run.py --category tool_schema --category subagent
    python run.py --model provider/model-name
    python run.py --proxy http://localhost:4000/v1
    python run.py --proxy http://localhost:4000/v1 --capture-dir /tmp/sw
    python run.py --clean            # wipe results first
    python run.py --timeout 120      # custom timeout

    # Local vLLM server (vllm/ prefix is auto-injected)
    python run.py --vllm http://localhost:8000/v1 --model Qwen/Qwen2.5-32B-Instruct
    python run.py --vllm http://localhost:8000/v1 --model Qwen/Qwen2.5-32B-Instruct --vllm-api-key token123
"""

import atexit
import json
import signal
import subprocess
import shutil
import sys
import argparse
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from common import ROOT, PROJECTS, RESULTS, CAPTURES, model_slug, load

DEFAULT_TIMEOUT = 180
DEFAULT_MAX_OUTPUT_TOKENS = 16384
# Fallback context window used when /v1/models doesn't expose max_model_len
# (or the server is unreachable). Kept conservative so opencode still sends
# a sane max_tokens rather than its hardcoded 32000 default, which routinely
# blows past (max_model_len - input_tokens) and raises ContextOverflowError.
FALLBACK_CONTEXT_TOKENS = 32768

_originals: dict[str, dict[str, bytes]] = {}

SKIP_DIRS = {"node_modules", "__pycache__"}


def _cleanup():
    for key in list(_originals):
        restore(Path(key))


atexit.register(_cleanup)
signal.signal(signal.SIGINT, lambda *_: sys.exit(1))
signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))


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


def _inject_proxy(cwd, provider, url):
    path = cwd / "opencode.json"
    cfg = json.loads(path.read_text()) if path.exists() else {}
    cfg.setdefault("provider", {}).setdefault(provider, {}).setdefault("options", {})["baseURL"] = url
    path.write_text(json.dumps(cfg, indent=2))


def _fetch_max_model_len(base_url, model_id, api_key="EMPTY", timeout=30):
    """Query an OpenAI-compatible `/v1/models` endpoint for max_model_len.

    vLLM (and most OpenAI-compatible servers) expose ``max_model_len`` as an
    integer field on each entry of ``data``. Returns ``None`` if the server
    is unreachable, returns a non-OK status, or doesn't include the field
    for ``model_id``.
    """
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        print(f"WARN: could not GET {url}: {e}", file=sys.stderr)
        return None
    for entry in data.get("data", []):
        if entry.get("id") == model_id:
            ctx = entry.get("max_model_len")
            if isinstance(ctx, int) and ctx > 0:
                return ctx
    return None


def _limit_for(context, max_output_tokens):
    """Build a `limit` block, clamping output so it can't meet or exceed context.

    opencode sends ``limit.output`` as ``max_tokens`` verbatim. The server
    rejects a request whenever ``max_tokens + input_tokens > max_model_len``,
    so we leave at least one token of headroom. Clamping to ``context - 1``
    is a belt-and-braces guard; callers should normally ensure there's enough
    room for a real prompt.
    """
    output = max(1, min(int(max_output_tokens), int(context) - 1))
    return {"context": int(context), "output": output}


def _patch_model_limits(max_output_tokens, api_key="EMPTY"):
    """Fill in ``limit.{context, output}`` on every project's opencode.json.

    For each ``projects/*/opencode.json`` that already has a custom provider
    with a ``baseURL``/``api`` pointing at an OpenAI-compatible server, we
    hit ``/v1/models``, look up ``max_model_len`` for each registered model,
    and write it onto the model entry as ``limit.context``. ``limit.output``
    is set from ``--max-output-tokens``.

    Results are cached per ``(base_url, model_id)`` so we only hit the server
    once even though all 12 project configs share the same provider config.

    Must run BEFORE ``snapshot(d)`` so the patched config is what gets
    restored between samples.
    """
    cache: dict[tuple[str, str], int | None] = {}
    fallback_used = False
    for d in sorted(PROJECTS.iterdir()):
        if not d.is_dir():
            continue
        path = d / "opencode.json"
        if not path.exists():
            continue
        cfg = json.loads(path.read_text())
        dirty = False
        for pcfg in cfg.get("provider", {}).values():
            base_url = pcfg.get("options", {}).get("baseURL") or pcfg.get("api")
            if not base_url:
                continue
            pkey = pcfg.get("options", {}).get("apiKey") or api_key
            for mid, mcfg in pcfg.get("models", {}).items():
                if not isinstance(mcfg, dict):
                    continue
                key = (base_url, mid)
                if key not in cache:
                    cache[key] = _fetch_max_model_len(base_url, mid, pkey)
                ctx = cache[key]
                if ctx is None:
                    ctx = FALLBACK_CONTEXT_TOKENS
                    fallback_used = True
                mcfg["limit"] = _limit_for(ctx, max_output_tokens)
                dirty = True
        if dirty:
            path.write_text(json.dumps(cfg, indent=2))
    if cache:
        resolved = {f"{u}#{m}": v for (u, m), v in cache.items()}
        print(f"Model limits: max_model_len={resolved}, "
              f"max_output_tokens={max_output_tokens}"
              + (f", fallback_context={FALLBACK_CONTEXT_TOKENS}" if fallback_used else ""))


def _inject_vllm_config(cwd, provider, model_id, server_url, api_key="EMPTY",
                        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
    """Inject a full vLLM provider config into a project's opencode.json.

    Mirrors the logic in run_cluster.py's build_config_inject_cmd but operates
    in-process. Registers the npm adapter, model entry, and baseURL so that
    opencode can resolve provider/model at runtime, and fills in
    ``limit.{context, output}`` using ``max_model_len`` from the server's
    ``/v1/models`` endpoint (falling back to ``FALLBACK_CONTEXT_TOKENS``).
    """
    path = cwd / "opencode.json"
    cfg = json.loads(path.read_text()) if path.exists() else {}

    ctx = _fetch_max_model_len(server_url, model_id, api_key) or FALLBACK_CONTEXT_TOKENS
    model_entry = {
        "name": model_id,
        "id": model_id,
        "limit": _limit_for(ctx, max_output_tokens),
    }
    provider_cfg = {
        "npm": "@ai-sdk/openai-compatible",
        "name": provider,
        "api": server_url,
        "env": [],
        "options": {"baseURL": server_url, "apiKey": api_key},
        "models": {model_id: model_entry},
    }

    cfg["disabled_providers"] = ["opencode"]
    cfg.setdefault("provider", {})[provider] = provider_cfg
    path.write_text(json.dumps(cfg, indent=2))


def run(sample, timeout, run_dir, model=None, proxy=None, provider=None,
        vllm_url=None, vllm_model_id=None, vllm_api_key="EMPTY",
        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
    sid = sample["id"]
    name = sample.get("name", str(sid))
    project = sample.get("project", "default")
    cwd = PROJECTS / project

    if not cwd.exists():
        print(f"  SKIP #{sid} {name}: project {project}/ not found")
        return None

    restore(cwd)
    if vllm_url:
        _inject_vllm_config(cwd, provider, vllm_model_id, vllm_url, vllm_api_key,
                            max_output_tokens=max_output_tokens)
    elif proxy:
        _inject_proxy(cwd, provider, proxy)
    print(f"  RUN  #{sid} {name} (project={project})", end="", flush=True)
    start = time.time()

    try:
        proc = subprocess.Popen(
            ["opencode", "run", "--format", "json"]
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

    if "Model not found" in stderr or "Invalid model" in stderr:
        print(f"\n  ERROR: {stderr.strip()}")
        sys.exit(1)

    out = run_dir / f"{sid}_{name}.jsonl"
    out.write_text(stdout)

    if stderr.strip():
        (run_dir / f"{sid}_{name}.err").write_text(stderr)

    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    tools = sum(1 for l in lines if '"tool_use"' in l)
    print(f"         {len(lines)} events, {tools} tool calls")

    return out


def main():
    subprocess.run(
        ["git", "checkout", "--", "projects/"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="Run specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Run all samples in a category")
    parser.add_argument("--clean", action="store_true", help="Wipe results first")
    parser.add_argument("--model", "-m", help="Model in provider/model format (default: opencode config)")
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
        "--capture-dir",
        default=None,
        help="Flat directory where switchyard writes captures. "
             "New files are moved to captures/{slug}/{timestamp}/ after the run. "
             "Defaults to captures/.",
    )
    parser.add_argument(
        "--vllm",
        default=None,
        help="vLLM server URL (e.g. http://localhost:8000/v1). "
             "Injects full provider config (npm adapter, model registration, baseURL) "
             "into each project's opencode.json. Requires --model in provider/model format.",
    )
    parser.add_argument(
        "--vllm-api-key",
        default="EMPTY",
        help="API key for the vLLM server (default: EMPTY)",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help=(
            "Cap for `max_tokens` on each opencode request. Written into each "
            "project's opencode.json as `provider.<p>.models.<m>.limit.output`. "
            "Without this, opencode hardcodes 32000 for custom providers and "
            "raises ContextOverflowError when it exceeds "
            "(max_model_len - input_tokens). Default: 16384."
        ),
    )
    args = parser.parse_args()

    if args.vllm and args.proxy:
        print("ERROR: --vllm and --proxy are mutually exclusive")
        sys.exit(1)

    if args.vllm and not args.model:
        print("ERROR: --vllm requires --model")
        sys.exit(1)

    # Auto-prefix provider when --vllm is used and model doesn't have one.
    # e.g. "Qwen/Qwen3.5-35B-A3B" -> "vllm/Qwen/Qwen3.5-35B-A3B"
    if args.vllm and args.model and not args.model.startswith("vllm/"):
        args.model = f"vllm/{args.model}"

    if args.model and "/" not in args.model:
        print(f"ERROR: --model must be in provider/model format (got '{args.model}')")
        sys.exit(1)

    if args.clean and RESULTS.exists():
        shutil.rmtree(RESULTS)
        print("Cleaned results/\n")

    # Patch opencode.json limits BEFORE snapshotting so the auto-detected
    # max_model_len / max_output_tokens survive restore() between samples.
    # In the --vllm path the provider config doesn't exist yet; it'll be
    # injected (with limits) per-sample inside run().
    if not args.vllm:
        _patch_model_limits(args.max_output_tokens)

    for d in PROJECTS.iterdir():
        if d.is_dir():
            snapshot(d)

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    slug = model_slug(args.model)
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = RESULTS / slug / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    provider = args.proxy_provider
    if args.vllm:
        provider = args.model.split("/")[0]
    elif args.proxy and not provider:
        provider = args.model.split("/")[0] if args.model else "nvidia"

    # model_id is the part after the provider prefix (e.g. "Qwen2.5-32B-Instruct"
    # from "vllm/Qwen2.5-32B-Instruct")
    vllm_model_id = None
    if args.vllm:
        vllm_model_id = args.model.split("/", 1)[1]

    meta = {
        "model": args.model,
        "model_slug": slug,
        "date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp": timestamp,
        "timeout": args.timeout,
        "samples": [s["id"] for s in samples],
        "categories": sorted(set(s["category"] for s in samples)),
        "proxy": args.proxy,
        "vllm": args.vllm,
        "max_output_tokens": args.max_output_tokens,
        "argv": sys.argv,
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    cap_src = Path(args.capture_dir) if args.capture_dir else CAPTURES
    existing = set(cap_src.glob("*.json")) if cap_src and cap_src.is_dir() else set()

    parts = []
    if args.model:
        parts.append(f"model={args.model}")
    if args.vllm:
        parts.append(f"vllm={args.vllm} (provider={provider}, model_id={vllm_model_id})")
    elif args.proxy:
        parts.append(f"proxy={args.proxy} ({provider})")
    label = f"{', '.join(parts)}, " if parts else ""
    print(f"Running {len(samples)} sample(s) ({label}timeout={args.timeout}s)")
    print(f"Run dir: {run_dir}\n")

    ran = 0
    skipped = 0
    for sample in samples:
        if run(sample, args.timeout, run_dir, model=args.model, proxy=args.proxy,
               provider=provider, vllm_url=args.vllm, vllm_model_id=vllm_model_id,
               vllm_api_key=args.vllm_api_key,
               max_output_tokens=args.max_output_tokens):
            ran += 1
        else:
            skipped += 1

    # Restore all project directories to their original state so that
    # injected provider configs (vllm, proxy) don't persist on disk.
    for d in PROJECTS.iterdir():
        if d.is_dir():
            restore(d)

    if cap_src and cap_src.is_dir():
        cap_dst = CAPTURES / slug / timestamp
        cap_dst.mkdir(parents=True, exist_ok=True)
        moved = 0
        for f in sorted(cap_src.glob("*.json")):
            if f not in existing:
                shutil.move(str(f), str(cap_dst / f.name))
                moved += 1
        if moved:
            print(f"\nMoved {moved} capture(s) to {cap_dst}/")

    print(f"\nDone. {ran} ran, {skipped} skipped")
    print(f"Results in {run_dir}/")


if __name__ == "__main__":
    main()
