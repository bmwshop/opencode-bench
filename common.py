import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLES = ROOT / "data" / "samples.jsonl"
PROJECTS = ROOT / "projects"
RUNS = ROOT / "runs"


def resolve_opencode_cmd(cmd=None, cwd=None):
    """Resolve the opencode command and cwd for subprocess.

    Precedence: explicit arg > env var > default.
      cmd: --opencode > $OPENCODE_BIN > "opencode"
      cwd: --opencode-cwd > $OPENCODE_CWD > None
    """
    raw = cmd or os.environ.get("OPENCODE_BIN") or "opencode"
    cwd = cwd or os.environ.get("OPENCODE_CWD") or None
    return shlex.split(raw), raw, cwd


def _git(args, cwd):
    try:
        r = subprocess.run(
            ["git", "-C", cwd or ".", *args],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def opencode_git(cwd):
    """Return git rev info for the opencode checkout, or None if not a git repo."""
    if not cwd:
        return None
    head = _git(["rev-parse", "HEAD"], cwd)
    if not head:
        return None
    status = _git(["status", "--porcelain"], cwd)
    return {
        "remote": _git(["remote", "get-url", "origin"], cwd),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd),
        "commit": head,
        "short": head[:7],
        "dirty": bool(status),
    }


def opencode_meta(cmd=None, cwd=None):
    """Best-effort snapshot of which opencode we're about to invoke.

    Returns a dict with version, cmd, cwd, executable (resolved path),
    and git info if the cwd is inside a git checkout.
    """
    argv, raw, cwd = resolve_opencode_cmd(cmd, cwd)
    try:
        r = subprocess.run(
            [*argv, "--version"], capture_output=True, text=True, timeout=30, cwd=cwd
        )
        version = (r.stdout.strip() or r.stderr.strip() or "unknown").splitlines()[-1]
    except (OSError, subprocess.SubprocessError):
        version = "unknown"
    exe = shutil.which(argv[0]) if argv else None
    return {
        "version": version,
        "cmd": raw,
        "cwd": cwd,
        "executable": exe,
        "git": opencode_git(cwd),
    }


def opencode_rev_label(meta):
    """One-line shorthand like '1.4.0' or 'local @ 33b2795+dirty'."""
    if not meta:
        return "?"
    g = meta.get("git") or {}
    rev = f" @ {g['short']}{'+dirty' if g.get('dirty') else ''}" if g else ""
    return f"{meta.get('version', '?')}{rev}"


SCHEMAS_PATH = ROOT / "data" / "tool_schemas.json"


def schema_meta():
    """Return the opencode-meta subset of data/tool_schemas.json, or None."""
    if not SCHEMAS_PATH.exists():
        return None
    try:
        d = json.loads(SCHEMAS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return {
        "version": d.get("opencode_version"),
        "git": d.get("opencode_git"),
        "cmd": d.get("opencode_cmd"),
        "cwd": d.get("opencode_cwd"),
        "executable": d.get("opencode_executable"),
        "tools": len(d.get("tools", {})),
        "extracted_at": d.get("extracted_at"),
    }


def compare_opencode(run_oc, sch_oc):
    """Compare runtime vs schema opencode meta.

    Returns (status, detail) where status is one of:
        "match"         -- both sides have equal git commits
        "match-version" -- both sides have equal release versions (no 'local')
        "mismatch"      -- git commits differ, or versions differ
        "unknown"       -- can't prove match or mismatch (mixed / missing info)
    """
    if not run_oc or not sch_oc:
        return "unknown", "metadata missing on one side"

    rg = (run_oc.get("git") or {}).get("commit")
    sg = (sch_oc.get("git") or {}).get("commit")
    rv = run_oc.get("version")
    sv = sch_oc.get("version")

    if rg and sg:
        if rg == sg:
            return "match", f"both @ {rg[:7]}"
        return "mismatch", f"git commit drift: runtime {rg[:7]}, schemas {sg[:7]}"

    if rv and sv and rv == sv and rv not in ("unknown", "local", "?"):
        return "match-version", f"both {rv}"

    if rv and sv and rv != sv:
        return (
            "mismatch",
            f"version drift: runtime {opencode_rev_label(run_oc)}, "
            f"schemas {opencode_rev_label(sch_oc)}",
        )

    return (
        "unknown",
        f"runtime {opencode_rev_label(run_oc)} vs schemas {opencode_rev_label(sch_oc)}",
    )


def model_slug(model):
    """Turn 'provider/model-name' into a filesystem-safe slug like 'provider_model-name'."""
    if not model:
        return "default"
    return re.sub(r"[/\\]+", "_", model)


def resolve_run(model=None, run=None):
    """Locate a run directory under runs/{model_slug}/{timestamp}/.

    Modes:
        model + run  -> exact: runs/{slug}/{run}/
        model only   -> latest timestamp under runs/{slug}/
        neither      -> latest timestamp across all runs/*/
    """
    if model and run:
        d = RUNS / model_slug(model) / run
        if not d.is_dir():
            return None
        return d

    if model:
        parent = RUNS / model_slug(model)
        return _latest_subdir(parent)

    if not RUNS.is_dir():
        return None
    best = None
    for model_dir in sorted(RUNS.iterdir()):
        if not model_dir.is_dir():
            continue
        candidate = _latest_subdir(model_dir)
        if candidate and (best is None or candidate.name > best.name):
            best = candidate
    return best


def _latest_subdir(parent):
    """Return the lexicographically last subdirectory (highest timestamp)."""
    if not parent.is_dir():
        return None
    dirs = sorted(
        (d for d in parent.iterdir() if d.is_dir()),
        key=lambda d: d.name,
    )
    return dirs[-1] if dirs else None


def list_runs():
    """Yield (model_slug, timestamp, meta_dict) for every run found."""
    if not RUNS.is_dir():
        return
    for model_dir in sorted(RUNS.iterdir()):
        if not model_dir.is_dir():
            continue
        for ts_dir in sorted(model_dir.iterdir()):
            if not ts_dir.is_dir():
                continue
            meta_path = ts_dir / "meta.json"
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            yield model_dir.name, ts_dir.name, meta


def load(args):
    with open(SAMPLES) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)
            if args.id and str(sample["id"]) not in args.id:
                continue
            if args.category and sample["category"] not in args.category:
                continue
            yield sample
