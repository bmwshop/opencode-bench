#!/usr/bin/env python3
"""
Propose v1 code-editing sample candidates for a pinned repo.

Walks `src/requests/` (or any scope), enumerates editable functions, and
ranks them by an editability score that approximates what makes a good
de-leaked editing sample:

  * loc            — bigger functions are easier to grep, harder to rewrite
                     blind; we want 5-30 LOC.
  * branches       — `if/elif/else/try/except` count; more branches = more
                     places where a guard clause can land naturally.
  * has_callers    — number of in-repo functions that call this one (hint
                     that a hard-tier multi-file edit could pair impl + caller).
  * docstring      — well-documented functions are easier to write a
                     behaviour contract for.
  * not_dunder     — skip `__init__` / property setters that are too
                     boilerplate to be interesting.

For each candidate we predict a difficulty tier (`easy` / `medium` / `hard`)
using the heuristic in `docs/building_editing_samples.md` and emit a
machine-readable JSON suitable for piping into
`scripts/score_editing_candidate.py`.

Filters out functions that are already targeted by an existing entry in
`data/v1_editing_criteria.json` (file + name match).

Usage
-----
    python3 scripts/propose_editing_candidates.py --top 15
    python3 scripts/propose_editing_candidates.py --tier hard --multi-file
    python3 scripts/propose_editing_candidates.py --format json > /tmp/edit_proposals.json
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MANIFEST_PATH = ROOT / "data" / "v1_editing_criteria.json"
V1_REPOS_PATH = ROOT / "data" / "v1_repos.json"
DEFAULT_REPO = "requests"


def _load_v1_repos() -> dict[str, Any]:
    return json.loads(V1_REPOS_PATH.read_text())


def repo_root(slug: str) -> Path:
    repos = _load_v1_repos()
    if slug not in repos:
        raise ValueError(
            f"unknown repo {slug!r}; v1_repos.json knows: {sorted(repos)}"
        )
    return ROOT / repos[slug]["submodule_path"]


def default_scope_for(slug: str) -> list[str]:
    repos = _load_v1_repos()
    scope = repos.get(slug, {}).get("default_scope", "")
    return [scope] if scope else [""]

# Editability bounds: too-small functions don't have room for a behaviour
# change; too-big ones are unrealistic for a single-edit sample.
LOC_MIN = 4
LOC_MAX = 35


# ---------------------------------------------------------------------------
# Existing-sample index
# ---------------------------------------------------------------------------


def existing_targets() -> set[tuple[str, str]]:
    if not MANIFEST_PATH.exists():
        return set()
    samples = json.loads(MANIFEST_PATH.read_text()).get("samples", [])
    out: set[tuple[str, str]] = set()
    for s in samples:
        f = s.get("file")
        for fn in s.get("functions", []) or []:
            out.add((f, fn))
        for t in s.get("targets", []) or []:
            for fn in t.get("functions", []) or []:
                out.add((t.get("path"), fn))
    return out


# ---------------------------------------------------------------------------
# Per-function editability metrics
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    file: str
    function: str
    qualname: str
    loc: int
    branches: int
    has_docstring: bool
    has_callers: int
    template_hint: str
    predicted_difficulty: str
    multi_file_pairing: list[dict[str, str]]
    score: float


def _branch_count(node: ast.AST) -> int:
    n = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.Try, ast.ExceptHandler, ast.For, ast.While)):
            n += 1
    return n


def _has_docstring(node: ast.AST) -> bool:
    body = getattr(node, "body", None) or []
    if not body:
        return False
    first = body[0]
    return (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )


def _template_hint(node: ast.AST) -> str:
    """Coarse classification of what kind of edit would suit this function."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        body = node.body
        # function with try/except — good for relax-validator (broaden except)
        if any(isinstance(c, ast.Try) for c in body):
            return "relax-validator"
        # function whose top is a guard `if not isinstance(...)` — already type-guarded
        if body and isinstance(body[0], ast.If):
            return "tighten-guard"
        # function whose body is dominated by a list/dict comprehension — extend-list candidate
        for c in ast.walk(node):
            if isinstance(c, (ast.ListComp, ast.DictComp, ast.SetComp)):
                return "extend-comprehension"
        # generator function — swap-impl candidate
        for c in ast.walk(node):
            if isinstance(c, ast.Yield):
                return "swap-generator"
    return "add-guard"


def _predict_difficulty(loc: int, branches: int, has_callers: int, multi_file: bool) -> str:
    if multi_file:
        return "hard"
    if loc <= 10 and branches <= 1 and has_callers <= 2:
        return "easy"
    if loc >= 18 or branches >= 3:
        return "hard"
    return "medium"


def _editability_score(loc: int, branches: int, has_docstring: bool, has_callers: int) -> float:
    # Sweet spot ~ 12 LOC, 2 branches, has a docstring, ~3 callers.
    score = 0.0
    score -= abs(loc - 12) / 6.0
    score -= abs(branches - 2) / 2.0
    score += 0.3 if has_docstring else -0.3
    score -= abs(has_callers - 3) / 4.0
    return round(score, 3)


# ---------------------------------------------------------------------------
# File walk (top-level functions per file)
# ---------------------------------------------------------------------------


def _expand_scope(scope: list[str], slug: str = DEFAULT_REPO) -> list[str]:
    root = repo_root(slug)
    out: list[str] = []
    for item in scope:
        rel = item.replace("\\", "/")
        full = root / rel.rstrip("/") if rel else root
        if full.is_dir():
            for p in sorted(full.rglob("*.py")):
                out.append(str(p.relative_to(root)).replace("\\", "/"))
        else:
            out.append(rel)
    return sorted(set(out))


def _toplevel_funcs(tree: ast.Module):
    """Yield (name, node) for every top-level function in a module."""
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n.name, n


# ---------------------------------------------------------------------------
# Caller fan-out (cheap approximate via name-match across all files)
# ---------------------------------------------------------------------------


def _calls_target(node: ast.AST, target_name: str) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name) and f.id == target_name:
                return True
            if isinstance(f, ast.Attribute) and f.attr == target_name:
                return True
    return False


def _name_callers(target_name: str, target_file: str, file_trees: dict) -> int:
    n = 0
    for f, tree in file_trees.items():
        for fn_name, fn_node in _toplevel_funcs(tree):
            if f == target_file and fn_name == target_name:
                continue
            if _calls_target(fn_node, target_name):
                n += 1
    return n


def _suggest_multifile_pairing(
    target_name: str,
    target_file: str,
    file_trees: dict,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen = set()
    for f, tree in file_trees.items():
        if f == target_file:
            continue
        for fn_name, fn_node in _toplevel_funcs(tree):
            if (f, fn_name) in seen:
                continue
            if _calls_target(fn_node, target_name):
                seen.add((f, fn_name))
                out.append({"file": f, "function": fn_name})
                if len(out) >= 3:
                    return out
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def collect_candidates(
    scope: list[str],
    multi_file: bool,
    top: int,
    tier_filter: str | None,
    slug: str = DEFAULT_REPO,
) -> list[Candidate]:
    root = repo_root(slug)
    expanded = _expand_scope(scope, slug)
    file_trees: dict[str, ast.Module] = {}
    for rel in expanded:
        try:
            src = (root / rel).read_text()
            file_trees[rel] = ast.parse(src, filename=rel)
        except (OSError, SyntaxError):
            continue
    skip = existing_targets()

    cands: list[Candidate] = []
    for rel, tree in file_trees.items():
        for fn_name, node in _toplevel_funcs(tree):
            if fn_name.startswith("__") and fn_name.endswith("__"):
                continue
            end = getattr(node, "end_lineno", None)
            loc = (end - node.lineno + 1) if end else 0
            if not (LOC_MIN <= loc <= LOC_MAX):
                continue
            if (rel, fn_name) in skip:
                continue

            callers = _name_callers(fn_name, rel, file_trees)
            branches = _branch_count(node)
            has_doc = _has_docstring(node)
            pairing = _suggest_multifile_pairing(fn_name, rel, file_trees) if multi_file else []
            if multi_file and not pairing:
                continue
            difficulty = _predict_difficulty(loc, branches, callers, multi_file=bool(pairing))
            if tier_filter and difficulty != tier_filter:
                continue
            cand = Candidate(
                file=rel,
                function=fn_name,
                qualname=fn_name,
                loc=loc,
                branches=branches,
                has_docstring=has_doc,
                has_callers=callers,
                template_hint=_template_hint(node),
                predicted_difficulty=difficulty,
                multi_file_pairing=pairing,
                score=_editability_score(loc, branches, has_doc, callers),
            )
            cands.append(cand)

    cands.sort(key=lambda c: -c.score)
    return cands[:top]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=DEFAULT_REPO,
                   help=f"Repo slug from data/v1_repos.json (default: {DEFAULT_REPO}).")
    p.add_argument("--scope", action="append", default=None,
                   help="Scope (file or directory) within the repo. Repeatable. "
                        "Defaults to the repo's `default_scope` from v1_repos.json.")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--tier", choices=["easy", "medium", "hard"])
    p.add_argument("--multi-file", action="store_true",
                   help="Only emit candidates with at least one cross-file caller.")
    p.add_argument("--format", choices=["json", "text"], default="text")
    p.add_argument("--output")
    args = p.parse_args()

    scope = args.scope or default_scope_for(args.repo)
    cands = collect_candidates(scope, args.multi_file, args.top, args.tier, args.repo)

    if args.format == "json":
        payload = [asdict(c) for c in cands]
        s = json.dumps(payload, indent=2)
    else:
        rows = []
        rows.append(
            f"{'file::function':<60} {'tier':<8} {'loc':>4} {'br':>3} {'callers':>7} "
            f"{'pair':>4} template-hint    score"
        )
        rows.append("-" * 120)
        for c in cands:
            tag = f"{c.file}::{c.qualname}"
            rows.append(
                f"{tag:<60} {c.predicted_difficulty:<8} {c.loc:>4} {c.branches:>3} "
                f"{c.has_callers:>7} {len(c.multi_file_pairing):>4} {c.template_hint:<16} {c.score:>5.2f}"
            )
        s = "\n".join(rows)

    if args.output:
        Path(args.output).write_text(s + "\n")
    else:
        print(s)

    return 0


if __name__ == "__main__":
    sys.exit(main())
