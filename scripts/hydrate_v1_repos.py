#!/usr/bin/env python3
"""
Materialize pinned v1 repos into projects/v1/* as clean git checkouts.

Use this inside a staged cluster container when `projects/v1/*` contains plain
files copied from git submodules but not the submodules' own `.git` metadata.
`run.py` validates v1 fixtures with `git rev-parse HEAD`, so the staged tree
must be repaired into real repos before v1 samples can run.

Usage:
    python scripts/hydrate_v1_repos.py
    python scripts/hydrate_v1_repos.py --repo requests
    python scripts/hydrate_v1_repos.py --dry-run
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import PROJECTS, v1_repos  # noqa: E402


def _run(cmd, cwd=None, check=True, capture_output=True):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def _git(path, *args, check=True):
    return _run(["git", "-C", str(path), *args], check=check)


def _repo_state(path):
    if not path.exists():
        return {"kind": "missing"}
    try:
        head = _git(path, "rev-parse", "HEAD").stdout.strip()
    except subprocess.CalledProcessError:
        return {"kind": "non_git"}
    status = _git(path, "status", "--porcelain").stdout.strip()
    return {
        "kind": "git",
        "head": head,
        "dirty": bool(status),
    }


def _remove_path(path):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _select_entries(requested):
    manifest = v1_repos()
    if not manifest:
        raise SystemExit("No v1 repos declared in data/v1_repos.json")

    names = requested or sorted(manifest)
    unknown = [name for name in names if name not in manifest]
    if unknown:
        raise SystemExit(
            "Unknown repo(s): "
            + ", ".join(sorted(unknown))
            + ". Known repos: "
            + ", ".join(sorted(manifest))
        )
    return [(name, manifest[name]) for name in names]


def _target_path(repo, entry):
    declared = entry.get("submodule_path", f"projects/v1/{repo}")
    expected = f"projects/v1/{repo}"
    if declared != expected:
        raise SystemExit(
            f"Repo {repo!r} declares submodule_path={declared!r}; "
            f"expected {expected!r}"
        )
    # Honor OPENCODE_BENCH_PROJECTS override via the PROJECTS constant; the
    # `projects/` prefix in the manifest's `submodule_path` is implicit
    # (PROJECTS already points at projects/), so we attach only the "v1/<repo>" tail.
    return PROJECTS / "v1" / repo


def hydrate(repo, entry, dry_run=False):
    target = _target_path(repo, entry)
    url = entry["url"]
    pin = entry["pin"]
    state = _repo_state(target)

    if state["kind"] == "git" and state["head"] == pin and not state["dirty"]:
        print(f"OK    {repo}: already at {pin[:12]} ({target})")
        return

    reason = state["kind"]
    if state["kind"] == "git":
        bits = [f"HEAD={state['head'][:12]}"]
        if state["dirty"]:
            bits.append("dirty")
        reason = ", ".join(bits)

    print(f"SYNC  {repo}: rebuilding {target} ({reason})")
    print(f"      clone {url}")
    print(f"      checkout {pin}")
    if dry_run:
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    _remove_path(target)
    _run(["git", "clone", url, str(target)], capture_output=False)
    _git(target, "checkout", pin, capture_output=False)

    final = _repo_state(target)
    if final["kind"] != "git":
        raise RuntimeError(f"{repo}: clone succeeded but {target} is not a git repo")
    if final["head"] != pin:
        raise RuntimeError(
            f"{repo}: expected HEAD {pin}, got {final['head']}"
        )
    if final["dirty"]:
        raise RuntimeError(f"{repo}: hydrated checkout is unexpectedly dirty")


def main():
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument(
        "--repo",
        action="append",
        default=None,
        help="Repo slug(s) from data/v1_repos.json to hydrate. Defaults to all.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the actions without modifying projects/v1/*.",
    )
    args = p.parse_args()

    entries = _select_entries(args.repo)
    print(
        f"Hydrating {len(entries)} v1 repo(s) under {PROJECTS / 'v1'}"
        + (" [dry-run]" if args.dry_run else "")
    )
    for repo, entry in entries:
        hydrate(repo, entry, dry_run=args.dry_run)
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
