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
    python run.py                    # run all v1 samples, every category (default)
    python run.py --version v0       # run all v0 samples (every category)
    python run.py --version v1       # run all v1 samples (every category)
    python run.py --category code_review  # narrow to one category
    python run.py --id 21            # run one sample (within selected version/category)
    python run.py --id 21 --id 22    # run multiple samples
    python run.py --category tool_schema
    python run.py --category tool_schema --category subagent
    python run.py --model provider/model-name
    python run.py --proxy http://localhost:4000/v1
    python run.py --proxy http://localhost:4000/v1 --capture-dir /tmp/sw
    python run.py --clean            # wipe runs/ first
    python run.py --timeout 120      # custom timeout
    python run.py --retry-on-timeout 2  # retry each sample up to 2x on TimeoutExpired
    python run.py --workers 4        # run up to 4 samples in parallel

    # Local vLLM server (vllm/ prefix is auto-injected)
    python run.py --vllm http://localhost:8000/v1 --model Qwen/Qwen2.5-32B-Instruct
    python run.py --vllm http://localhost:8000/v1 --model Qwen/Qwen2.5-32B-Instruct --vllm-api-key token123
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from common import (
    ROOT, PROJECTS, RUNS, CAPTURE_STAGING,
    model_slug, load,
    opencode_meta, opencode_rev_label, resolve_opencode_cmd,
    schema_meta, compare_opencode,
    project_dir, run_project_name, trace_name,
    v1_repos, v1_repo_pin,
)

DEFAULT_TIMEOUT = 180
DEFAULT_MAX_OUTPUT_TOKENS = 8192


def _assert_fixture_clean(src: Path, auto_repair: bool = True) -> None:
    """Guard against seeding a run from a contaminated source tree.

    v1 fixtures are git submodules; nothing in the bench ever writes to them,
    but IDE autosave / formatters / stray agent edits / `__pycache__` have
    contaminated them before (see run 2026-04-22T05-18-24 for #12, formerly #4). A dirty
    source silently poisons every run that copies it, so we check up-front.

    ``git status --porcelain`` returns empty output for a clean working tree
    (tracked modifications + untracked files; ignored files not included).
    When the tree is dirty, behavior depends on ``auto_repair``:

    - ``auto_repair=True`` (default): print a WARNING with the diff, then run
      ``git checkout -- . && git clean -fdx`` to reset to HEAD, then continue.
      Fixtures are meant to be immutable; any working-tree drift is junk.
    - ``auto_repair=False``: raise ``RuntimeError``. The unhandled exception
      propagates out of the ThreadPoolExecutor / main(), aborting the entire
      eval (not just the current sample) — we want loud failure, not partial
      runs against a contaminated fixture.

    No-op if ``src`` is not a git repo (e.g., v0 fixtures at projects/v0/NNN/).
    """
    if not (src / ".git").exists():
        return
    r = subprocess.run(
        ["git", "-C", str(src), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    dirty = r.stdout.strip()
    if not dirty:
        return
    if auto_repair:
        print(
            f"  WARNING: fixture {src} was dirty; auto-repairing to HEAD.\n"
            f"  Dropped working-tree state:\n{dirty}",
            flush=True,
        )
        subprocess.run(["git", "-C", str(src), "checkout", "--", "."], check=True)
        subprocess.run(["git", "-C", str(src), "clean", "-fdx"], check=True)
        return
    raise RuntimeError(
        f"Fixture {src} is dirty; refusing to seed a run from a contaminated "
        f"source tree. ABORTING ENTIRE EVAL.\n\n"
        f"Working-tree status:\n{dirty}\n\n"
        f"Fix options:\n"
        f"  (1) rerun without --no-auto-repair-fixtures (default auto-repairs to HEAD)\n"
        f"  (2) manually reset:  git -C {src} checkout -- . && git -C {src} clean -fdx"
    )
# Guards `_capture_subagents` against runaway recursion (a subagent spawning
# another subagent etc.). Independent of opencode's own runtime limits.
MAX_SUBAGENT_DEPTH = 8
# `task` tool outputs begin with `task_id: ses_XXX (for resuming ...)\n\n...`
# (see packages/opencode/src/tool/task.ts). First capture group is the child
# session id that `opencode export` can read back from the SQLite store.
_TASK_ID_RE = re.compile(r"^task_id:\s*(ses_\w+)", re.M)
# Fallback context window used when /v1/models doesn't expose max_model_len
# (or the server is unreachable). Kept conservative so opencode still sends
# a sane max_tokens rather than its hardcoded 32000 default, which routinely
# blows past (max_model_len - input_tokens) and raises ContextOverflowError.
FALLBACK_CONTEXT_TOKENS = 32768
# CAPTURE_STAGING is imported from common.py; honors OPENCODE_BENCH_CAPTURES.

# Shared across worker threads so multiple parallel run()s don't each hit
# /v1/models for the same (base_url, model_id) pair.
_ctx_cache: dict[tuple[str, str], int | None] = {}
_ctx_cache_lock = threading.Lock()


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


def _cached_context(base_url, model_id, api_key):
    """Thread-safe cached lookup of max_model_len for (base_url, model_id)."""
    key = (base_url, model_id)
    with _ctx_cache_lock:
        if key in _ctx_cache:
            return _ctx_cache[key]
    # Fetch outside the lock so slow HTTP calls don't serialize workers.
    ctx = _fetch_max_model_len(base_url, model_id, api_key)
    with _ctx_cache_lock:
        _ctx_cache.setdefault(key, ctx)
        return _ctx_cache[key]


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


def _patch_model_limits_in(cwd, max_output_tokens, api_key="EMPTY"):
    """Fill in ``limit.{context, output}`` on a single project's opencode.json.

    For each custom provider in ``cwd/opencode.json`` that has a
    ``baseURL``/``api`` pointing at an OpenAI-compatible server, we
    hit ``/v1/models``, look up ``max_model_len`` for each registered model,
    and write it onto the model entry as ``limit.context``. ``limit.output``
    is set from ``max_output_tokens``.

    Without this, opencode hardcodes 32000 for custom providers and routinely
    raises ContextOverflowError when max_tokens + input_tokens exceeds
    max_model_len.
    """
    path = cwd / "opencode.json"
    if not path.exists():
        return
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
            ctx = _cached_context(base_url, mid, pkey)
            if ctx is None:
                ctx = FALLBACK_CONTEXT_TOKENS
            mcfg["limit"] = _limit_for(ctx, max_output_tokens)
            dirty = True
    if dirty:
        path.write_text(json.dumps(cfg, indent=2))


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

    ctx = _cached_context(server_url, model_id, api_key) or FALLBACK_CONTEXT_TOKENS
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


def _scan_parent_for_task_sids(text):
    """Return [(child_sid, parent_sid), ...] for each `task` tool_use in a
    run.py parent trace (JSONL from `opencode run --format json`)."""
    out = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") != "tool_use":
            continue
        part = evt.get("part", {})
        if part.get("tool") != "task":
            continue
        output = part.get("state", {}).get("output", "")
        m = _TASK_ID_RE.search(output)
        if m:
            out.append((m.group(1), evt.get("sessionID", "")))
    return out


def _scan_sidecar_for_task_sids(text):
    """Return [(child_sid, parent_sid), ...] for each `task` part in an
    exported session JSON (stdout of `opencode export <sid>`)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    parent_sid = data.get("info", {}).get("id", "")
    out = []
    for msg in data.get("messages", []):
        for p in msg.get("parts", []):
            if p.get("type") != "tool":
                continue
            if p.get("tool") != "task":
                continue
            m = _TASK_ID_RE.search(p.get("state", {}).get("output", ""))
            if m:
                out.append((m.group(1), parent_sid))
    return out


def _capture_subagents(trace_path, cwd, argv):
    """BFS over task tool calls in the parent trace + any emitted sidecars.
    Exports each unseen subagent session via `opencode export` and writes a
    sidecar at `{stem}.subagent-{sid[-10:]}.json` next to the trace. A visited
    set guards cycles; MAX_SUBAGENT_DEPTH guards runaways. Best-effort: any
    per-sid failure is logged and does not abort the caller."""
    try:
        parent_text = trace_path.read_text()
    except OSError:
        return
    # Prefilter: samples without delegation pay zero cost.
    if '"tool":"task"' not in parent_text:
        return

    stem = trace_path.stem
    tag = f"#{stem.split('_', 1)[0]}"
    queue = [(sid, 1, psid) for sid, psid in _scan_parent_for_task_sids(parent_text)]
    visited = set()
    while queue:
        sid, depth, parent_sid = queue.pop(0)
        if sid in visited:
            continue
        visited.add(sid)
        if depth >= MAX_SUBAGENT_DEPTH:
            print(f"WARN  {tag} subagent depth cap hit at {sid} (depth {depth})", flush=True)
            continue
        sidecar = trace_path.with_name(f"{stem}.subagent-{sid[-10:]}.json")
        # Route stdout directly to the sidecar file (not through subprocess.PIPE):
        # `opencode export` exits without awaiting the pipe drain event, so any
        # output past the OS's ~64KiB pipe buffer is silently dropped when we
        # read via PIPE. Writing straight to a file bypasses the pipe entirely.
        try:
            with open(sidecar, "wb") as fh:
                proc = subprocess.run(
                    [*argv, "export", sid],
                    cwd=cwd,
                    stdout=fh, stderr=subprocess.PIPE,
                    timeout=60, check=False,
                )
            if proc.returncode != 0:
                stderr_tail = (proc.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()[-1:]
                raise RuntimeError(f"rc={proc.returncode} {stderr_tail}")
            sidecar_text = sidecar.read_text()
        except Exception as e:
            print(f"WARN  {tag} subagent export failed: {sid} (depth {depth}): {e}", flush=True)
            # Leave a partial file rather than delete it -- easier to inspect.
            continue
        for child_sid, child_parent in _scan_sidecar_for_task_sids(sidecar_text):
            if child_sid not in visited:
                queue.append((child_sid, depth + 1, child_parent))


def run(sample, timeout, run_dir, model=None, proxy=None, provider=None,
        vllm_url=None, vllm_model_id=None, vllm_api_key="EMPTY",
        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
        retry_on_timeout=0, cap_src=None, auto_repair_fixtures=False):
    sid = sample["id"]
    name = sample.get("name", str(sid))
    src = project_dir(sample)

    if not src.is_dir():
        rel = src.relative_to(ROOT) if src.is_absolute() else src
        print(f"  SKIP #{sid} {name}: {rel}/ not found", flush=True)
        return None

    _assert_fixture_clean(src, auto_repair=auto_repair_fixtures)

    cwd = run_dir / "projects" / run_project_name(sample)
    if cwd.exists():
        shutil.rmtree(cwd)
    cwd.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, cwd)

    # Workspace-overlay merge: layer per-sample overlay files (AGENTS.md /
    # opencode.json / .opencode/agents/<name>.md / fixture files) on top of
    # the parent's repo copy. Each category that supports overlays maps to
    # its own subdir under projects/v1/. Manifest is single source of truth;
    # overlays are written by the per-family derive_*.py script.
    _overlay_subdir_by_category = {
        "tool_restriction": "mutants",
        "tool_restriction_mutant": "mutants",  # legacy pre-rename rows
        "orchestration": "orchestration",
        "skill": "skills",
    }
    overlay_subdir = _overlay_subdir_by_category.get(sample.get("category"))
    if overlay_subdir:
        overlay_src = PROJECTS / "v1" / overlay_subdir / f"{sid:03d}"
        if overlay_src.is_dir():
            for item in overlay_src.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(overlay_src)
                    dst = cwd / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dst)

    if vllm_url:
        _inject_vllm_config(cwd, provider, vllm_model_id, vllm_url, vllm_api_key,
                            max_output_tokens=max_output_tokens)
    else:
        # Patch limits on any pre-existing custom providers so opencode
        # doesn't send its default 32000 max_tokens and trip ContextOverflow.
        _patch_model_limits_in(cwd, max_output_tokens)
        if proxy:
            _inject_proxy(cwd, provider, proxy)

    header = f"  RUN  #{sid:03d} {name}"
    argv, _, _ = resolve_opencode_cmd()
    popen_argv = (
        [*argv, "run", "--format", "json"]
        + (["--model", model] if model else [])
        + (["--agent", sample["agent"]] if "agent" in sample else [])
        + [sample["prompt"]]
    )

    max_attempts = 1 + max(0, retry_on_timeout)
    stdout, stderr = "", ""
    timed_out = False
    elapsed = 0.0
    attempt = 0
    for attempt in range(1, max_attempts + 1):
        cap_snapshot = (
            set(cap_src.glob("*.json"))
            if (cap_src is not None and cap_src.is_dir())
            else None
        )
        start = time.time()
        try:
            proc = subprocess.Popen(
                popen_argv,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = time.time() - start
            timed_out = False
            break
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
            elapsed = time.time() - start
            timed_out = True
            if attempt < max_attempts:
                if cap_snapshot is not None:
                    # Discard failed-attempt captures so only the final attempt's land on disk.
                    for f in cap_src.glob("*.json"):
                        if f not in cap_snapshot:
                            try:
                                f.unlink()
                            except OSError:
                                pass
                print(
                    f"{header}  TIMEOUT ({elapsed:.0f}s) \u2014 retrying "
                    f"{attempt + 1}/{max_attempts}",
                    flush=True,
                )
                continue
            break
        except FileNotFoundError:
            print(f"  ERROR: opencode not found in PATH", flush=True)
            sys.exit(1)

    if timed_out:
        header += (
            f"  TIMEOUT ({timeout}s x{attempt})"
            if attempt > 1
            else f"  TIMEOUT ({elapsed:.0f}s)"
        )
    else:
        header += (
            f"  ({elapsed:.0f}s, retry {attempt}/{max_attempts})"
            if attempt > 1
            else f"  ({elapsed:.0f}s)"
        )

    if "Model not found" in stderr or "Invalid model" in stderr:
        print(f"{header}\n  ERROR: {stderr.strip()}", flush=True)
        sys.exit(1)

    stem = trace_name(sample)

    if timed_out:
        # Invariant: no trace on disk unless opencode completed inside the
        # timeout budget. Python loop variables persist after the loop, so
        # cap_snapshot here is the snapshot taken at the start of the final
        # attempt; prune anything the final attempt produced.
        if cap_snapshot is not None:
            for f in cap_src.glob("*.json"):
                if f not in cap_snapshot:
                    try:
                        f.unlink()
                    except OSError:
                        pass
        print(f"{header} \u2014 dropped", flush=True)
        return None

    out = run_dir / f"{stem}.jsonl"
    out.write_text(stdout)

    if stderr.strip():
        (run_dir / f"{stem}.err").write_text(stderr)

    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    tools = sum(1 for l in lines if '"tool_use"' in l)

    _capture_subagents(out, cwd, argv)

    sub_tools = 0
    sidecars = sorted(run_dir.glob(f"{stem}.subagent-*.json"))
    for sc in sidecars:
        try:
            data = json.loads(sc.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for msg in data.get("messages", []):
            sub_tools += sum(1 for p in msg.get("parts", []) if p.get("type") == "tool")
    suffix = f" (+{sub_tools} in {len(sidecars)} subagent(s))" if sidecars else ""
    # Single write so `--workers > 1` can't splice header and stats across
    # samples. POSIX guarantees writes <= PIPE_BUF are atomic.
    print(f"{header}\n         {len(lines)} events, {tools} tool calls{suffix}", flush=True)

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
    parser.add_argument(
        "--category",
        action="append",
        help="Run all samples in a category. May be passed multiple times to "
             "select a union of categories. When omitted, every category in "
             "the selected --version runs. Pass `--category all` as an "
             "explicit no-op equivalent to omitting the flag.",
    )
    parser.add_argument(
        "--version",
        choices=["v0", "v1"],
        default="v1",
        help="Benchmark version to run. A single run targets exactly one "
             "version (default: v1). Run v0 separately with --version v0.",
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
        "--retry-on-timeout",
        type=int,
        default=0,
        metavar="N",
        help="On TimeoutExpired, retry the sample up to N additional times "
             "(default: 0). Only the final attempt's trace/captures are kept.",
    )
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
        "--vllm",
        default=None,
        help="vLLM server URL (e.g. http://localhost:8000/v1). "
             "Injects full provider config (npm adapter, model registration, baseURL) "
             "into each per-sample opencode.json. Requires --model in provider/model format.",
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
            "(max_model_len - input_tokens). Default: 8192."
        ),
    )
    parser.add_argument(
        "--skip-schema-check",
        action="store_true",
        help="Skip the preflight that refuses to run when the opencode "
             "runtime doesn't match data/tool_schemas.json (only enforced "
             "when any sample uses call_schema_valid).",
    )
    parser.add_argument(
        "--auto-repair-fixtures",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If the fixture source tree (projects/<version>/<repo>/) is dirty, "
             "print a WARNING and reset it to HEAD (git checkout -- . && git "
             "clean -fdx) before copying. Default: on. Pass --no-auto-repair-fixtures "
             "to fail loudly instead (aborts the entire eval, not just the sample).",
    )
    args = parser.parse_args()

    # Default behaviour: with no --id and no --category, run every sample in
    # the selected --version (default v1). The legacy "default to
    # code_localization on v1" behaviour was relaxed -- `--version` flag is
    # now treated identically whether explicit or implicit.
    # `--category all` remains accepted as an explicit no-op for back-compat.
    if args.category and "all" in args.category:
        args.category = None

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
    if args.vllm:
        provider = args.model.split("/")[0]
    elif args.proxy and not provider:
        provider = args.model.split("/")[0] if args.model else "nvidia"

    # model_id is the part after the provider prefix (e.g. "Qwen2.5-32B-Instruct"
    # from "vllm/Qwen2.5-32B-Instruct")
    vllm_model_id = None
    if args.vllm:
        vllm_model_id = args.model.split("/", 1)[1]

    v1_repos_used = sorted({s["repo"] for s in samples if s.get("version") == "v1" and s.get("repo")})
    meta = {
        "model": args.model,
        "model_slug": slug,
        "date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp": timestamp,
        "timeout": args.timeout,
        "retry_on_timeout": args.retry_on_timeout,
        "samples": [s["id"] for s in samples],
        "categories": sorted(set(s["category"] for s in samples)),
        "version": args.version,
        "v1_repo_pins": {r: v1_repo_pin(r) for r in v1_repos_used},
        "proxy": args.proxy,
        "vllm": args.vllm,
        "max_output_tokens": args.max_output_tokens,
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
    if args.vllm:
        parts.append(f"vllm={args.vllm} (provider={provider}, model_id={vllm_model_id})")
    elif args.proxy:
        parts.append(f"proxy={args.proxy} ({provider})")
    if args.workers > 1:
        parts.append(f"workers={args.workers}")
    label = f"{', '.join(parts)}, " if parts else ""
    retry_suffix = (
        f", retry_on_timeout={args.retry_on_timeout}"
        if args.retry_on_timeout > 0
        else ""
    )
    print(f"Running {len(samples)} sample(s) ({label}timeout={args.timeout}s{retry_suffix})")
    print(f"Run dir: {run_dir}\n")

    ran = 0
    skipped = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [
            ex.submit(
                run, sample, args.timeout, run_dir,
                model=args.model, proxy=args.proxy, provider=provider,
                vllm_url=args.vllm, vllm_model_id=vllm_model_id,
                vllm_api_key=args.vllm_api_key,
                max_output_tokens=args.max_output_tokens,
                retry_on_timeout=args.retry_on_timeout,
                cap_src=cap_src,
                auto_repair_fixtures=args.auto_repair_fixtures,
            )
            for sample in samples
        ]
        for f in as_completed(futures):
            if f.result():
                ran += 1
            else:
                skipped += 1

    if _ctx_cache:
        resolved = {f"{u}#{m}": v for (u, m), v in _ctx_cache.items()}
        print(f"\nModel limits: max_model_len={resolved}, "
              f"max_output_tokens={args.max_output_tokens}, "
              f"fallback_context={FALLBACK_CONTEXT_TOKENS}")

    if cap_src.is_dir():
        _move_captures(run_dir, cap_src, existing)

    print(f"\nDone. {ran} ran, {skipped} skipped")
    print(f"Run in {run_dir}/")


if __name__ == "__main__":
    main()
