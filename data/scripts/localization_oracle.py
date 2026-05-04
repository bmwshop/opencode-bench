#!/usr/bin/env python3
"""
Shared oracle for v1 structured-output code-localization samples (#21-#30).

Every sample in this family formulates a ground-truth set of functions in a
pinned Python codebase (currently psf/requests @ 79f4df84cf77) and emits a
deterministic gold file whose each line is `file_path::QualifiedName`.

QualifiedName policy ("dotted everywhere"):
    - Module-level function     -> bare name              (e.g. `merge_cookies`)
    - Method on a class         -> `ClassName.method`     (e.g. `Session.send`)
    - Method on nested class    -> `Outer.Inner.method`
    - Nested (closure) function -> `outer.inner`          (e.g. `iter_content.generate`)

The gold string is:
    sorted(entries, key=str) joined by "\\n" + trailing "\\n".

Two templates are supported:

    T1: anchor + direct callers
        One "anchor" function is named. The answer is the anchor itself
        (as `file::QualifiedName`) plus every function, at any nesting
        depth in any file under `scope`, whose body contains a direct call
        resolving by name to the anchor. "Direct call" means an `ast.Call`
        whose `func` is either `Name(id=anchor)` or `Attribute(attr=anchor)`.

    T2: callers-of-set (optionally constructor semantics)
        A set of target NAMES is given. The answer is every function whose
        body contains a direct call resolving by name to ANY target. The
        target defs/classes themselves are NOT in the answer (unlike T1).

Every public helper is pure and side-effect free except where it invokes
`rg` via subprocess for cross-check; the latter is opt-in.

Typical use from a per-sample `derive_0NN_ground_truth.py`:

    from scripts.localization_oracle import (
        anchor_and_callers, callers_of_set, emit_gold, build_pattern,
        check_module_level_uniqueness, cross_check_rg_calls, sha256_gold,
    )

    result = anchor_and_callers(
        anchor_file="src/requests/cookies.py",
        anchor_name="merge_cookies",
        scope=["src/requests/cookies.py", "src/requests/sessions.py"],
        require_module_level_anchor=True,
    )
    gold = emit_gold(result.entries)
    check_module_level_uniqueness("src/requests/cookies.py", "merge_", [result.anchor.name])
    cross_check_rg_calls(result.scope_files, "merge_cookies", result.call_sites)
    print(gold)
    print(sha256_gold(gold))
"""
from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import PROJECTS  # noqa: E402

V1_REQUESTS_ROOT = PROJECTS / "v1" / "requests"

# ---------------------------------------------------------------------------
# AST walk: every FunctionDef/AsyncFunctionDef annotated with its dotted qualname
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FuncInfo:
    file: str                    # repo-relative forward-slashed path
    qualname: str                # dotted qualified name per policy above
    name: str                    # bare func name
    lineno: int                  # def line (1-indexed)
    end_lineno: int              # last line of body (1-indexed, inclusive)
    is_method: bool              # True iff nested inside a ClassDef (any depth)
    class_chain: tuple[str, ...] # enclosing class names, outermost-first

    @property
    def entry(self) -> str:
        """`file::qualname` gold entry."""
        return f"{self.file}::{self.qualname}"


def walk_functions(
    tree: ast.AST,
    *,
    file: str,
) -> list[FuncInfo]:
    """Yield FuncInfo for every function at any nesting depth in `tree`.

    `file` is the repo-relative path to record. The walker tracks enclosing
    ClassDef / FunctionDef / AsyncFunctionDef names so it can construct the
    dotted qualname per policy.
    """
    out: list[FuncInfo] = []

    def _recurse(node: ast.AST, scope: tuple[str, ...], class_chain: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                _recurse(child, scope + (child.name,), class_chain + (child.name,))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = ".".join(scope + (child.name,)) if scope else child.name
                end = child.body[-1].end_lineno if child.body and child.body[-1].end_lineno else child.lineno
                out.append(
                    FuncInfo(
                        file=file,
                        qualname=qual,
                        name=child.name,
                        lineno=child.lineno,
                        end_lineno=end,
                        is_method=bool(class_chain),
                        class_chain=class_chain,
                    )
                )
                # Functions introduce a scope for nested funcs but NOT a class chain
                # (a function inside a class body produces `Class.method`, but a
                # function inside a function gives `outer.inner`, not `Class.outer.inner`
                # -- class_chain tracks classes only).
                _recurse(child, scope + (child.name,), class_chain)
            else:
                _recurse(child, scope, class_chain)

    _recurse(tree, (), ())
    return out


# ---------------------------------------------------------------------------
# Repo-wide analysis for the sample proposer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FuncAnalysis:
    """Extended per-function stats used by the sample proposer.

    Wraps a FuncInfo with information the proposer needs to score candidate
    T1 anchors and T2 target sets: decorator presence, nested-def presence,
    async kind, attribute-call resolution stats for calls made inside the
    body, and a rough "anchor kind" label matching the structural-signature
    vocabulary used in `data/v1_localization_criteria.json`.
    """
    info: FuncInfo
    has_decorator: bool
    decorator_names: tuple[str, ...]
    is_async: bool
    has_nested_def: bool
    anchor_kind: str                # one of: module_level, instance_method,
                                    # mixin_method, classmethod, staticmethod,
                                    # property, async_method, nested_closure
    call_names: tuple[str, ...]     # unique callee names invoked in body
    calls_self: bool                # body contains a call whose name matches
                                    # this function's own bare name


def _classify_anchor_kind(node: ast.AST, fi: FuncInfo) -> str:
    """Heuristic kind label for a function node.

    Order of precedence: decorator-based > async > structural.
    """
    decorators: list[str] = []
    for d in getattr(node, "decorator_list", []) or []:
        if isinstance(d, ast.Name):
            decorators.append(d.id)
        elif isinstance(d, ast.Attribute):
            decorators.append(d.attr)
        elif isinstance(d, ast.Call):
            f = d.func
            if isinstance(f, ast.Name):
                decorators.append(f.id)
            elif isinstance(f, ast.Attribute):
                decorators.append(f.attr)
    if "classmethod" in decorators:
        return "classmethod"
    if "staticmethod" in decorators:
        return "staticmethod"
    if "property" in decorators:
        return "property"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_method" if fi.is_method else "async_function"
    if len(fi.qualname.split(".")) > len(fi.class_chain) + 1:
        return "nested_closure"
    if fi.is_method:
        chain_lower = " ".join(c.lower() for c in fi.class_chain)
        if "mixin" in chain_lower:
            return "mixin_method"
        return "instance_method"
    return "module_level"


def _body_call_names(node: ast.AST) -> tuple[list[str], bool, str]:
    """Return (unique_callee_names, has_nested_def, calls_self_name).

    `calls_self_name` is the bare name of the function itself if its body
    calls it recursively (detected by a bare `Name(id=<name>)` call), else ""
    (we still return it so callers can match by name without a second walk).
    """
    names: set[str] = set()
    has_nested = False
    own_name = getattr(node, "name", "")
    self_call = False
    for n in ast.walk(node):
        if n is node:
            continue
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_nested = True
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                names.add(f.id)
                if own_name and f.id == own_name:
                    self_call = True
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return sorted(names), has_nested, own_name if self_call else ""


def analyze_scope(scope: str | list[str]) -> list[FuncAnalysis]:
    """Return a FuncAnalysis for every function defined in `scope`.

    Used by `data/scripts/propose_localization_candidates.py` to build its per-
    function index. Accepts the same scope shapes as `_normalize_scope` so
    the proposer and the deriver talk about the same files.
    """
    scope_files = _normalize_scope(scope)
    out: list[FuncAnalysis] = []
    for rel in scope_files:
        tree, _ = _read_tree(rel)
        for fi in walk_functions(tree, file=rel):
            node = _func_ast_by_info(tree, fi)
            decorators = tuple(
                (d.id if isinstance(d, ast.Name)
                 else d.attr if isinstance(d, ast.Attribute)
                 else (d.func.id if isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Name)
                       else d.func.attr if isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Attribute)
                       else ""))
                for d in (getattr(node, "decorator_list", []) or [])
            )
            decorators = tuple(d for d in decorators if d)
            call_names, has_nested, self_call_name = _body_call_names(node)
            out.append(
                FuncAnalysis(
                    info=fi,
                    has_decorator=bool(decorators),
                    decorator_names=decorators,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    has_nested_def=has_nested,
                    anchor_kind=_classify_anchor_kind(node, fi),
                    call_names=tuple(call_names),
                    calls_self=bool(self_call_name),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Call resolution
# ---------------------------------------------------------------------------


def _calls_matching(func_node: ast.AST, predicate: Callable[[str], bool]) -> list[int]:
    """Line numbers of every `ast.Call` inside `func_node` whose callee name
    satisfies `predicate(name)`. Resolves both `name(...)` and `obj.name(...)`.
    """
    lines: list[int] = []
    for n in ast.walk(func_node):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        cand: str | None = None
        if isinstance(fn, ast.Name):
            cand = fn.id
        elif isinstance(fn, ast.Attribute):
            cand = fn.attr
        if cand and predicate(cand):
            lines.append(n.lineno)
    return sorted(lines)


def _func_ast_by_info(tree: ast.AST, info: FuncInfo) -> ast.AST:
    """Locate the ast node corresponding to a FuncInfo by matching lineno + name."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno == info.lineno and n.name == info.name:
                return n
    raise LookupError(f"could not re-locate {info.qualname} at {info.file}:{info.lineno}")


# ---------------------------------------------------------------------------
# High-level templates
# ---------------------------------------------------------------------------


@dataclass
class T1Result:
    """Result of an "anchor + direct callers" derivation."""
    anchor: FuncInfo
    callers: list[FuncInfo]
    call_sites: dict[str, list[int]] = field(default_factory=dict)
    # entries already sorted lex.
    entries: list[str] = field(default_factory=list)
    scope_files: list[str] = field(default_factory=list)


@dataclass
class T2Result:
    """Result of a "callers-of-set" derivation."""
    targets: list[str]
    callers: list[FuncInfo]
    call_sites: dict[str, list[int]] = field(default_factory=dict)
    entries: list[str] = field(default_factory=list)
    scope_files: list[str] = field(default_factory=list)


def _read_tree(file_rel: str) -> tuple[ast.Module, str]:
    path = V1_REQUESTS_ROOT / file_rel
    src = path.read_text()
    return ast.parse(src, filename=str(path)), src


def _normalize_scope(scope: str | list[str]) -> list[str]:
    """Normalize scope to a sorted list of repo-relative forward-slashed .py paths.

    Accepts:
        - a single directory rel path (e.g. "src/requests/") -> recursive .py glob
        - a list of file rel paths -> used as-is
    """
    if isinstance(scope, list):
        out = sorted({p.replace("\\", "/") for p in scope})
        for rel in out:
            full = V1_REQUESTS_ROOT / rel
            if not full.is_file():
                raise FileNotFoundError(f"scope file does not exist: {rel}")
        return out
    # directory case
    rel = scope.replace("\\", "/").rstrip("/")
    base = V1_REQUESTS_ROOT / rel
    if not base.is_dir():
        raise FileNotFoundError(f"scope dir does not exist: {rel}")
    paths = sorted(
        str(p.relative_to(V1_REQUESTS_ROOT)).replace("\\", "/")
        for p in base.rglob("*.py")
    )
    return paths


def anchor_and_callers(
    *,
    anchor_file: str,
    anchor_name: str,
    scope: str | list[str],
    require_module_level_anchor: bool = True,
    allow_decorators: bool = False,
) -> T1Result:
    """T1: find the anchor and every direct caller of it under `scope`.

    Anchor is identified by name + file. The scope is searched for FunctionDef
    nodes whose bodies contain a direct call whose callee resolves by name to
    `anchor_name`.

    The anchor's own file may be inside `scope`; the anchor itself is added to
    the answer exactly once. If the anchor calls itself (recursion), that
    function is NOT counted as a caller (would produce a duplicate entry).
    """
    anchor_tree, _ = _read_tree(anchor_file)
    anchor_funcs = walk_functions(anchor_tree, file=anchor_file)
    matching = [f for f in anchor_funcs if f.name == anchor_name]
    if require_module_level_anchor:
        matching = [f for f in matching if not f.is_method]
    if len(matching) != 1:
        kind = "module-level " if require_module_level_anchor else ""
        raise AssertionError(
            f"expected exactly one {kind}function named {anchor_name!r} in "
            f"{anchor_file}, found {len(matching)}"
        )
    anchor = matching[0]
    if not allow_decorators:
        node = _func_ast_by_info(anchor_tree, anchor)
        if getattr(node, "decorator_list", None):
            raise AssertionError(
                f"{anchor.qualname} at {anchor.file}:{anchor.lineno} has decorators; "
                f"anchor convention forbids them. Pass allow_decorators=True to relax."
            )

    scope_files = _normalize_scope(scope)

    callers: list[FuncInfo] = []
    call_sites: dict[str, list[int]] = {}
    pred = lambda n: n == anchor_name
    for rel in scope_files:
        tree, _ = _read_tree(rel)
        for f in walk_functions(tree, file=rel):
            if f.file == anchor.file and f.qualname == anchor.qualname:
                continue  # skip anchor itself in caller list
            node = _func_ast_by_info(tree, f)
            lines = _calls_matching(node, pred)
            if lines:
                callers.append(f)
                call_sites[f"{f.file}::{f.qualname}"] = lines

    entries = sorted([anchor.entry] + [c.entry for c in callers])
    return T1Result(
        anchor=anchor,
        callers=callers,
        call_sites=call_sites,
        entries=entries,
        scope_files=scope_files,
    )


def callers_of_set(
    *,
    targets: list[str],
    scope: str | list[str],
    exclude_target_defs: bool = True,
) -> T2Result:
    """T2: find every function that directly calls any name in `targets`.

    The targets themselves are not added to the answer when
    `exclude_target_defs=True` (the default and the plan's convention).

    Self-calls within a target's own FunctionDef are excluded (so a target
    that recursively calls itself is not a "caller").

    Populates a per-target call-site map under
    `result.call_sites_by_target[target_name]` for cross-check convenience.
    """
    target_set = set(targets)
    scope_files = _normalize_scope(scope)

    callers: list[FuncInfo] = []
    call_sites: dict[str, list[int]] = {}
    by_target: dict[str, dict[str, list[int]]] = {t: {} for t in target_set}
    pred = lambda n: n in target_set

    for rel in scope_files:
        tree, _ = _read_tree(rel)
        for f in walk_functions(tree, file=rel):
            if exclude_target_defs and f.name in target_set:
                continue
            node = _func_ast_by_info(tree, f)
            lines = _calls_matching(node, pred)
            if not lines:
                continue
            callers.append(f)
            call_sites[f.entry] = lines
            # Per-target attribution: re-walk the caller body, classify each call.
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    fn = n.func
                    cand = (
                        fn.id if isinstance(fn, ast.Name)
                        else fn.attr if isinstance(fn, ast.Attribute)
                        else None
                    )
                    if cand in target_set:
                        by_target[cand].setdefault(f.entry, []).append(n.lineno)

    entries = sorted(c.entry for c in callers)
    result = T2Result(
        targets=sorted(targets),
        callers=callers,
        call_sites=call_sites,
        entries=entries,
        scope_files=scope_files,
    )
    # Attach per-target map as an attribute (not part of the dataclass schema
    # but useful for cross-checks).
    result.__dict__["call_sites_by_target"] = {
        t: {k: sorted(v) for k, v in m.items()}
        for t, m in by_target.items()
    }
    return result


def cross_check_rg_calls_t2(result: T2Result) -> None:
    """Run `rg` cross-check per target for a T2 result."""
    per_target = result.__dict__.get("call_sites_by_target", {})
    for target in result.targets:
        sites = per_target.get(target, {})
        if sites:
            cross_check_rg_calls(result.scope_files, target, sites)


# ---------------------------------------------------------------------------
# Sanity checks + cross-check
# ---------------------------------------------------------------------------


def check_module_level_uniqueness(
    file_rel: str,
    name_prefix: str,
    expected_names: list[str],
) -> None:
    """Assert that the module-level functions in `file_rel` whose names start
    with `name_prefix` are exactly `expected_names` (order-insensitive).

    Used to defend "unique reasonable pick" claims in each spec.
    """
    tree, _ = _read_tree(file_rel)
    got = [
        n.name for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith(name_prefix)
    ]
    if sorted(got) != sorted(expected_names):
        raise AssertionError(
            f"uniqueness check failed in {file_rel}: expected module-level "
            f"`{name_prefix}*` funcs to be {sorted(expected_names)}, got {sorted(got)}"
        )


def cross_check_rg_calls(
    scope_files: list[str],
    name: str,
    call_sites: dict[str, list[int]],
) -> None:
    """Cross-check AST call sites against `rg -n -w --with-filename <name> <files>`.

    Every AST call line must appear in rg output. Every rg line must either
    fall inside a known caller-body range or be a module-level reference
    (import / attribute of module). Catches AST/rg drift.
    """
    cmd = ["rg", "-n", "-w", "--with-filename", name, *scope_files]
    proc = subprocess.run(
        cmd,
        cwd=str(V1_REQUESTS_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"rg failed (rc={proc.returncode}): {proc.stderr.strip()}"
        )

    # Collect (file, lineno) pairs.
    rg_hits: set[tuple[str, int]] = set()
    for ln in proc.stdout.splitlines():
        m = re.match(r"(.+?):(\d+):", ln)
        if m:
            rg_hits.add((m.group(1).replace("\\", "/"), int(m.group(2))))

    # Every AST call line must be in rg.
    ast_hits: set[tuple[str, int]] = set()
    for key, lines in call_sites.items():
        file = key.split("::", 1)[0]
        for ln in lines:
            ast_hits.add((file, ln))

    missing = ast_hits - rg_hits
    if missing:
        raise AssertionError(
            f"AST found call sites not present in `rg -n -w {name}`: "
            f"{sorted(missing)}.\nrg stdout head: {proc.stdout[:500]!r}"
        )


# ---------------------------------------------------------------------------
# Gold + pattern + digest
# ---------------------------------------------------------------------------


def emit_gold(entries: list[str]) -> str:
    """Return the final sorted, newline-joined gold string with trailing newline."""
    sorted_entries = sorted(entries)
    return "\n".join(sorted_entries) + "\n"


def build_pattern(gold: str) -> str:
    """Anchored regex for `file_regex_disk`. Trailing newline is optional."""
    no_trailing = gold.rstrip("\n")
    lines = no_trailing.split("\n")
    escaped = [re.escape(line) for line in lines]
    body = r"\n".join(escaped)
    return rf"\A{body}\n?\Z"


def sha256_gold(gold: str) -> str:
    return hashlib.sha256(gold.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def submodule_head_sha(short: bool = False) -> str:
    """Return the current `projects/v1/requests` HEAD SHA."""
    r = subprocess.run(
        ["git", "-C", str(V1_REQUESTS_ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=5,
    )
    sha = r.stdout.strip()
    return sha[:12] if short else sha


# ---------------------------------------------------------------------------
# CLI runner shared by all `data/scripts/derive_0NN_ground_truth.py`
# ---------------------------------------------------------------------------


def run_derive_cli(
    *,
    sample_id: int,
    difficulty: str,
    template: str,
    result: T1Result | T2Result,
    json_only: bool,
    extra_checks: list[str] | None = None,
) -> dict[str, Any]:
    """Standard CLI epilogue shared across all derive scripts.

    Emits the gold, pattern, sha256, and either a human-readable or JSON
    summary; returns the payload dict for programmatic consumers.
    """
    gold = emit_gold(result.entries)
    pattern = build_pattern(gold)
    digest = sha256_gold(gold)
    sha = submodule_head_sha()

    payload = {
        "sample_id": sample_id,
        "difficulty": difficulty,
        "template": template,
        "pin": sha,
        "gold": gold,
        "pattern": pattern,
        "sha256": digest,
        "result": result_to_dict(result),
    }

    if json_only:
        print_str = __import__("json").dumps(payload, indent=2)
        print(print_str)
        return payload

    print(f"Sample #{sample_id}   (difficulty={difficulty}, template={template})")
    print(f"Submodule pin: {sha}")
    if isinstance(result, T1Result):
        print(f"Anchor:        {result.anchor.entry}  (def line {result.anchor.lineno})")
    else:
        print(f"Targets:       {result.targets}")
    print(f"Scope files:   {result.scope_files}")
    print("Checks:        AST + rg cross-check  PASS", end="")
    if extra_checks:
        print(f"  (+ {', '.join(extra_checks)})", end="")
    print()
    print()
    print("--- Gold answer (exact location.txt contents) ---")
    import sys as _sys
    _sys.stdout.write(gold)
    print("--- End gold ---")
    print(f"SHA-256 of gold: {digest}")
    print("--- Anchored regex for file_regex_disk ---")
    print(pattern)
    print()
    print("Entries + call sites:")
    if isinstance(result, T1Result):
        a = result.anchor
        print(f"  {a.entry}   (anchor; def line {a.lineno})")
        for c in result.callers:
            sites = result.call_sites.get(c.entry, [])
            print(f"  {c.entry}   (def line {c.lineno}; direct calls at {sites})")
    else:
        for c in result.callers:
            sites = result.call_sites.get(c.entry, [])
            print(f"  {c.entry}   (def line {c.lineno}; direct calls at {sites})")
    return payload


def result_to_dict(result: T1Result | T2Result) -> dict[str, Any]:
    """Serialize a T1/T2 result to a plain dict for JSON dumping."""
    base: dict[str, Any] = {
        "entries": result.entries,
        "call_sites": {k: v for k, v in result.call_sites.items()},
        "scope_files": result.scope_files,
    }
    if isinstance(result, T1Result):
        base["template"] = "T1"
        base["anchor"] = {
            "file": result.anchor.file,
            "qualname": result.anchor.qualname,
            "lineno": result.anchor.lineno,
        }
        base["callers"] = [
            {"file": c.file, "qualname": c.qualname, "lineno": c.lineno}
            for c in result.callers
        ]
    else:
        base["template"] = "T2"
        base["targets"] = result.targets
        base["callers"] = [
            {"file": c.file, "qualname": c.qualname, "lineno": c.lineno}
            for c in result.callers
        ]
    return base
