import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLES_V0 = ROOT / "data" / "samples_v0.jsonl"
SAMPLES_V1 = ROOT / "data" / "samples_v1.jsonl"
PROJECTS = ROOT / "projects"
RUNS = Path(os.environ["OPENCODE_BENCH_RUNS"]) if "OPENCODE_BENCH_RUNS" in os.environ else ROOT / "runs"
V1_REPOS_PATH = ROOT / "data" / "v1_repos.json"

SAMPLES_FILES = [("v0", SAMPLES_V0), ("v1", SAMPLES_V1)]

# Back-compat alias for any external caller still importing SAMPLES.
SAMPLES = SAMPLES_V0


_v1_repos_cache = None


def v1_repos():
    """Load data/v1_repos.json (memoized). Returns {} if the file is missing."""
    global _v1_repos_cache
    if _v1_repos_cache is not None:
        return _v1_repos_cache
    if not V1_REPOS_PATH.exists():
        _v1_repos_cache = {}
        return _v1_repos_cache
    _v1_repos_cache = json.loads(V1_REPOS_PATH.read_text())
    return _v1_repos_cache


def v1_repo_pin(repo):
    """Return the declared pin SHA for a v1 repo slug, or None if unknown."""
    entry = v1_repos().get(repo)
    return entry.get("pin") if entry else None


def project_dir(sample):
    """Canonical source fixture path for a sample.

    v0: projects/v0/NNN/
    v1: projects/v1/<repo>/  (submodule path from v1_repos.json)
    """
    version = sample.get("version", "v0")
    sid = sample["id"]
    if version == "v0":
        return PROJECTS / "v0" / f"{sid:03d}"
    if version == "v1":
        repo = sample.get("repo")
        if not repo:
            raise ValueError(f"v1 sample {sid} missing 'repo' field")
        entry = v1_repos().get(repo)
        if not entry:
            raise ValueError(f"v1 sample {sid} references unknown repo {repo!r}")
        declared = entry.get("submodule_path", f"projects/v1/{repo}")
        expected = f"projects/v1/{repo}"
        assert declared == expected, (
            f"repo {repo!r} submodule_path={declared!r} does not match expected {expected!r}"
        )
        return PROJECTS / "v1" / repo
    raise ValueError(f"unknown sample version: {version!r}")


def run_project_name(sample):
    """Subdir name inside run_dir/projects/ for a given sample."""
    return f"{sample['id']:03d}"


def trace_name(sample):
    """Trace filename stem inside run_dir/ for a given sample."""
    return f"{sample['id']:03d}_{sample.get('name', str(sample['id']))}"


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


def _version_roots(version=None):
    """Yield (version, dir) for each runs/{version}/ root to consider."""
    if version:
        yield version, RUNS / version
        return
    if not RUNS.is_dir():
        return
    for d in sorted(RUNS.iterdir()):
        if d.is_dir() and d.name in ("v0", "v1"):
            yield d.name, d


def _latest_subdir(parent):
    """Return the lexicographically last subdirectory (highest timestamp)."""
    if not parent.is_dir():
        return None
    dirs = sorted((d for d in parent.iterdir() if d.is_dir()), key=lambda d: d.name)
    return dirs[-1] if dirs else None


def resolve_run(model=None, run=None, version=None):
    """Locate a run directory under runs/{version}/{model_slug}/{timestamp}/.

    Modes:
        model + run            -> exact: runs/{version or search}/{slug}/{run}/
        model only             -> latest timestamp under runs/{version or search}/{slug}/
        neither                -> latest timestamp across the whole runs/ tree

    When `version` is None, searches v0 then v1 and returns the latest match.
    """
    slug = model_slug(model) if model else None
    best = None
    for _v, vroot in _version_roots(version):
        if slug and run:
            d = vroot / slug / run
            if d.is_dir():
                return d
            continue
        if slug:
            candidate = _latest_subdir(vroot / slug)
        else:
            candidate = None
            for model_dir in sorted(vroot.iterdir()) if vroot.is_dir() else []:
                if not model_dir.is_dir():
                    continue
                c = _latest_subdir(model_dir)
                if c and (candidate is None or c.name > candidate.name):
                    candidate = c
        if candidate and (best is None or candidate.name > best.name):
            best = candidate
    return best


def version_of(run_dir):
    """Extract version ('v0'/'v1') from a runs/{version}/{slug}/{ts}/ path."""
    try:
        v = run_dir.parent.parent.name
    except AttributeError:
        return None
    return v if v in ("v0", "v1") else None


def list_runs(version=None):
    """Yield (version, model_slug, timestamp, meta_dict) for every run found."""
    for v, vroot in _version_roots(version):
        if not vroot.is_dir():
            continue
        for model_dir in sorted(vroot.iterdir()):
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
                yield v, model_dir.name, ts_dir.name, meta


def load(args):
    """Yield samples from a single version's samples file, applying filters.

    A run targets exactly one version (v0 or v1). Callers pass `args.version`
    as a single string; if omitted, samples from all configured files are
    yielded (used by tooling that scans across runs).

    Filters:
        args.version  - string, e.g. "v0" or "v1", or None for no filter.
        args.id       - list of sample ids (as strings).
        args.category - list of category strings.
    """
    want_version = getattr(args, "version", None)
    for sample_version, path in SAMPLES_FILES:
        if want_version and sample_version != want_version:
            continue
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                sample.setdefault("version", sample_version)
                if args.id and str(sample["id"]) not in args.id:
                    continue
                if args.category and sample["category"] not in args.category:
                    continue
                yield sample
