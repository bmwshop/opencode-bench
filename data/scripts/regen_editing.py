#!/usr/bin/env python3
"""
Regenerate criterion-anchored code-editing samples (v1 #51-#60) from
`data/v1_editing_criteria.json`.

The manifest is the single source of truth. For each sample entry it lists:

    id, name        - sample id (51..60), short name
    difficulty      - "easy" | "medium" | "hard"; controls prompt template
                      and gate strictness. Defaults to "medium".
    leak_function_name - bool. True (easy) -> function name allowed
                      verbatim in prompt. False (medium / hard) -> function
                      name MUST NOT appear. Defaults to (difficulty=="easy").
    structural_signature - {template, scope_kind, answer_shape,
                      unique_trait} for diversity tracking. Mirrors the
                      localization manifest.
    behavior_prose  - the natural-language behavior contract that
                      replaces the leaked truth table in the prompt.
                      Multi-paragraph string, every literal/exception
                      that the asserts depend on must appear verbatim.
    file            - repo-relative path to the source file to edit
                      (single-file form). Mutually exclusive with
                      `targets`.
    targets         - list of {path, functions, constants, imports,
                      reference_edit, [is_new]} for multi-file
                      (hard-tier) edits. Mutually exclusive with `file`.
                      `is_new: true` marks a target whose listed
                      functions are SYNTHETIC helpers the agent must
                      CREATE (added by the reference edit). Names on
                      such targets are exempt from the function-name
                      hiding gate, since the prompt must name what to
                      add.
    functions       - top-level function(s) to AST-extract for exec_assert
                      (the target + any in-file callees it needs).
                      Used in the single-file form.
    constants       - top-level literal assignments to inject into the
                      exec_assert namespace (e.g. module-level HOOKS).
                      Single-file only; multi-file uses per-target lists.
    imports         - stdlib modules to `__import__` into the namespace.
    reference_edit  - {oldString, newString} demonstrating one valid fix
                      (single-file form).
    discovery_probes - rg patterns derived from the prompt's key terms;
                      the authoring gate enforces D in [2, 4] where
                      D = |union of rg -l hits across all probes|.
    asserts         - classified list of {expr, kind, misstep, [setup]}
                      entries. Every assert must pass against the
                      reference-edited file(s); each has
                          kind    in {regression, new_behavior}
                          misstep in {no-change, partial-edit, over-edit,
                                      syntax-error, none}
    mutants         - optional list of misstep-tagged mutation patches
                      `{misstep, patch: {oldString, newString} | null,
                        path?}`. Each must FAIL >= 1 assert (validated
                      by data/scripts/score_editing_candidate.py).
    prompt_capability  - 1-2 sentences that frame the target without
                         naming the file path; renders into the spec.
    prompt_required_literals - optional list of strings that MUST appear
                      verbatim in the prompt (literal-coverage gate).
                      The authoring gate adds exception classes and
                      `'X' in str(e)` substrings automatically.
    prompt_fail_modes  - 3 concrete ways the edit can go wrong (used to
                         seed the spec's "Fail modes" section)

For each entry this script:

    1. Verifies the reference edit's `oldString` occurs exactly once in
       the pinned file (authoring-gate anchor-uniqueness pre-check).
    2. Applies the edit to an in-memory copy of the file, AST-parses
       the result to confirm it's syntactically valid.
    3. Computes the canonical prompt (fully deterministic: names the
       target function, pins every asserted name + literal + exception
       class + input->output pair, lists the asserts verbatim as a
       truth table, and explicitly forbids naming the target file).
    4. Runs each `discovery_probes` entry as `rg -l <pattern> <scope>`
       against the pinned submodule for the entry's repo (read from
       `data/v1_repos.json[<repo>].default_scope`), takes the union, and
       verifies D in [2, 4].
    5. Rewrites `data/specs/v1/<NNN>_<name>.md` using `SPEC_TEMPLATE`.
    6. Deletes any stale spec files in the editing id range (51..90)
       whose filename no longer matches the current manifest name.
    7. Rewrites / appends the corresponding rows in
       `data/samples_v1.jsonl` (replacing existing rows in place;
       appending if absent). Each row has exactly 2 checks
       (`exec_assert` + `call_schema_valid`), category='code_editing',
       min_calls=3.

This is a deliberate extension of the mechanical-criterion pattern
established for v1 #21-#30 (see data/scripts/regen_localization.py).
Localization pins the oracle as `rg -l -w -e <tok> ...`; editing pins
the oracle as the literal list of Python assertions that the patched
function must satisfy. In both cases the prompt embeds enough of the
oracle that a faithful agent can self-verify its answer.

Usage
-----
    python3 data/scripts/regen_editing.py           # regenerate everything
    python3 data/scripts/regen_editing.py --dry-run # print plan, no writes
    python3 data/scripts/regen_editing.py --id 51   # just one sample
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_editing_criteria.json"
V1_REPOS_PATH = ROOT / "data" / "v1_repos.json"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"

DISCOVERY_MIN = 2
DISCOVERY_MAX = 4

# Default repo for entries that omit the `repo` field. Preserves backward
# compatibility for the original #51-60 manifest entries that pre-date the
# multi-repo generalization.
DEFAULT_REPO = "requests"


def _load_v1_repos() -> dict[str, Any]:
    return json.loads(V1_REPOS_PATH.read_text())


def repo_for(entry: dict) -> str:
    """Return the repo slug for a manifest entry; default to DEFAULT_REPO."""
    return entry.get("repo") or DEFAULT_REPO


def repo_root(slug: str) -> Path:
    """Resolve a repo slug to the per-run pinned source-tree root."""
    repos = _load_v1_repos()
    if slug not in repos:
        raise ValueError(
            f"unknown repo {slug!r}; v1_repos.json knows: {sorted(repos)}"
        )
    return ROOT / repos[slug]["submodule_path"]


def discovery_scope_for(slug: str) -> str:
    """Resolve a repo slug to the rg discovery-scope path (relative to the
    submodule root). Falls back to '' which scans the whole repo if a repo
    entry doesn't declare a default_scope."""
    repos = _load_v1_repos()
    return repos.get(slug, {}).get("default_scope", "")

# Fuzz words banned from prompts. The prompt must pin behavior with
# concrete names, values, and input->output pairs -- not open-ended
# modifiers that require the agent to exercise judgment.
FUZZ_WORDS = (
    r"\breasonable\b",
    r"\bappropriate\b",
    r"\bsensible\b",
    r"\bgenerally\b",
    r"\busually\b",
    r"\bas needed\b",
    r"\bwhere (?:it )?makes sense\b",
    r"\bif you think\b",
    r"\bsuitable\b",
)
FUZZ_RE = re.compile("|".join(FUZZ_WORDS), re.IGNORECASE)

VALID_MISSTEPS = {"no-change", "partial-edit", "over-edit", "syntax-error", "none"}
VALID_KINDS = {"regression", "new_behavior"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _difficulty(entry: dict) -> str:
    d = entry.get("difficulty") or "medium"
    if d not in VALID_DIFFICULTIES:
        raise ValueError(f"invalid difficulty {d!r}; valid: {sorted(VALID_DIFFICULTIES)}")
    return d


def _leak_fn_flag(entry: dict) -> bool:
    flag = entry.get("leak_function_name")
    if flag is None:
        return _difficulty(entry) == "easy"
    return bool(flag)


def targets_of(entry: dict) -> list[dict]:
    """Normalize a manifest entry to a list of target dicts.

    Each target dict has: path, functions, constants, imports, reference_edit.
    """
    if entry.get("targets"):
        out = []
        for t in entry["targets"]:
            out.append({
                "path": t["path"],
                "functions": list(t.get("functions") or []),
                "constants": list(t.get("constants") or []),
                "imports": list(t.get("imports") or []),
                "reference_edit": t["reference_edit"],
                "is_new": bool(t.get("is_new", False)),
            })
        return out
    return [{
        "path": entry["file"],
        "functions": list(entry.get("functions") or []),
        "constants": list(entry.get("constants") or []),
        "imports": list(entry.get("imports") or []),
        "reference_edit": entry["reference_edit"],
        "is_new": False,
    }]


def primary_function(entry: dict) -> str:
    """Best-effort 'the' function name for the sample (first target's first fn)."""
    targets = targets_of(entry)
    return targets[0]["functions"][0]


def all_function_names(entry: dict) -> list[str]:
    out: list[str] = []
    for t in targets_of(entry):
        out.extend(t["functions"])
    return out


def _exception_classes(asserts: list[dict]) -> list[str]:
    exc_re = re.compile(r"except\s+(\w+)")
    out: set[str] = set()
    for a in asserts:
        for exc in exc_re.findall(a.get("setup") or ""):
            out.add(exc)
    return sorted(out)


def _substring_literals(asserts: list[dict]) -> list[str]:
    """Extract every `'X' in str(...)` literal from assert exprs.

    These are the substrings the audit requires to appear verbatim in the
    prompt so the agent knows exactly what string to embed in a raised
    exception's message.
    """
    out: set[str] = set()
    for a in asserts:
        try:
            tree = ast.parse(a["expr"], mode="eval")
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Compare)
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.In)
                and isinstance(node.left, ast.Constant)
                and isinstance(node.left.value, str)
            ):
                out.add(node.left.value)
    return sorted(out)


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open() as f:
        return json.load(f)


def pin_short(slug: str = DEFAULT_REPO) -> str:
    try:
        repos = _load_v1_repos()
        sha = repos.get(slug, {}).get("pin") or ""
        return sha[:12] if sha else "unknown"
    except (json.JSONDecodeError, OSError):
        return "unknown"


# ---------------------------------------------------------------------------
# Reference-edit application + AST checks
# ---------------------------------------------------------------------------


def read_target_file(rel_path: str, slug: str = DEFAULT_REPO) -> str:
    p = repo_root(slug) / rel_path
    return p.read_text()


def apply_reference_edit(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(
            f"reference oldString occurs {count} times (expected exactly 1)"
        )
    return source.replace(old, new, 1)


def assert_ast_has_symbols(source: str, functions: list[str], constants: list[str]) -> None:
    tree = ast.parse(source)
    func_names = {
        n.name
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    const_names: set[str] = set()
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                if isinstance(tgt, ast.Name):
                    const_names.add(tgt.id)
        elif (
            isinstance(n, ast.AnnAssign)
            and isinstance(n.target, ast.Name)
            and n.value is not None
        ):
            const_names.add(n.target.id)
    missing_fns = [f for f in functions if f not in func_names]
    if missing_fns:
        raise ValueError(f"function(s) not found as top-level AST node: {missing_fns}")
    missing_consts = [c for c in constants if c not in const_names]
    if missing_consts:
        raise ValueError(f"constant(s) not found as top-level Assign: {missing_consts}")


# ---------------------------------------------------------------------------
# Discovery probe (D-gate)
# ---------------------------------------------------------------------------


def discovery_files(probes: list[str], slug: str = DEFAULT_REPO) -> list[str]:
    """Return sorted union of files matching any probe under the repo's scope."""
    scope = discovery_scope_for(slug)
    cwd = repo_root(slug)
    seen: set[str] = set()
    for pat in probes:
        cmd = ["rg", "-l", pat, scope] if scope else ["rg", "-l", pat]
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
        if proc.returncode not in (0, 1):
            raise RuntimeError(
                f"rg failed (rc={proc.returncode}) for pattern {pat!r}\n"
                f"stderr: {proc.stderr.strip()}"
            )
        for ln in proc.stdout.splitlines():
            ln = ln.strip().replace("\\", "/")
            if ln:
                seen.add(ln)
    return sorted(seen)


# ---------------------------------------------------------------------------
# Assert classification sanity
# ---------------------------------------------------------------------------


def classify_asserts(asserts: list[dict]) -> None:
    kinds = [a.get("kind") for a in asserts]
    missteps = [a.get("misstep") for a in asserts]
    for i, k in enumerate(kinds):
        if k not in VALID_KINDS:
            raise ValueError(f"assert #{i} has invalid kind {k!r}; valid: {sorted(VALID_KINDS)}")
    for i, m in enumerate(missteps):
        if m not in VALID_MISSTEPS:
            raise ValueError(f"assert #{i} has invalid misstep {m!r}; valid: {sorted(VALID_MISSTEPS)}")
    if "regression" not in kinds:
        raise ValueError("need at least one 'regression' assert")
    if "new_behavior" not in kinds:
        raise ValueError("need at least one 'new_behavior' assert")


# ---------------------------------------------------------------------------
# Prompt + row rendering
# ---------------------------------------------------------------------------


def _assert_line(a: dict) -> str:
    """Render one assert as a truth-table line (setup on same line if present)."""
    expr = a["expr"]
    setup = a.get("setup")
    if setup:
        collapsed = " ; ".join(s.strip() for s in setup.splitlines() if s.strip())
        return f"# setup: {collapsed}\nassert {expr}"
    return f"assert {expr}"


def build_prompt(entry: dict) -> str:
    """De-leaked prompt template.

    The behavior contract is in prose (entry["behavior_prose"]). The
    function name appears verbatim only when leak_function_name=true
    (default for easy tier). Hard-tier samples promise the agent that
    the change requires edits in two files.
    """
    difficulty = _difficulty(entry)
    leak_fn = _leak_fn_flag(entry)
    targets = targets_of(entry)
    multi = len(targets) > 1
    fn = primary_function(entry)
    capability = entry.get("prompt_capability", "").strip()
    prose = entry.get("behavior_prose", "").strip()
    if not prose:
        raise ValueError(f"#{entry['id']}: behavior_prose is required for de-leaked prompts")

    exc_classes = _exception_classes(entry["asserts"])

    repo = repo_for(entry)
    scope = discovery_scope_for(repo) or ""
    scope_path = f"`{scope}`" if scope else "the repo"

    parts: list[str] = []
    if leak_fn and not multi:
        parts.append(
            f"Modify the function `{fn}` inside the `{repo}` package so that the "
            f"behavior contract below holds:"
        )
    elif multi:
        parts.append(
            f"In this `{repo}` checkout, satisfy the cross-file behavior contract "
            f"below. The change requires consistent edits in TWO related files inside "
            f"{scope_path}. Find the relevant files by searching the repo for the "
            f"behavior described."
        )
    else:
        parts.append(
            f"In this `{repo}` checkout, locate the helper described below and patch "
            f"it so that the behavior contract holds. The helper lives somewhere under "
            f"{scope_path}; find it by searching the repo for the behavior described."
        )

    if capability:
        parts.append("")
        parts.append(f"> {capability}")
    parts.append("")
    parts.append("Behavior contract:")
    parts.append("")
    parts.append(prose)

    parts.append("")
    parts.append("Constraints:")
    if multi:
        parts.append(
            f"- Edit exactly TWO files inside {scope_path} (one impl + one caller "
            f"that depends on it). Do not add new files."
        )
    else:
        parts.append(f"- Edit exactly ONE file inside {scope_path}. Do not add new files.")
    parts.append(
        "- Preserve every behavior not explicitly changed by the contract above; "
        "regression-style behavior must continue to hold."
    )
    if exc_classes:
        cls_list = ", ".join(f"`{c}`" for c in exc_classes)
        parts.append(
            f"- Use exactly the exception class(es) named in the contract ({cls_list}); "
            f"other classes will not satisfy the hidden grader."
        )
    parts.append("- Keep the edit minimal and localized; do not refactor unrelated code.")

    return "\n".join(parts)


def _checks_for_row(entry: dict) -> list[dict]:
    """Build the exec_assert + call_schema_valid checks list for the row."""
    targets = targets_of(entry)
    asserts = [
        {k: v for k, v in a.items() if k in ("expr", "setup")}
        for a in entry["asserts"]
    ]
    n_asserts = len(asserts)
    fn = primary_function(entry)

    if len(targets) == 1:
        t = targets[0]
        exec_chk = {
            "type": "exec_assert",
            "path": t["path"],
            "functions": list(t["functions"]),
            "constants": list(t["constants"]),
            "imports": list(t["imports"]),
            "asserts": asserts,
            "timeout": 10,
            "description": (
                f"function `{fn}` in `{t['path']}` satisfies all "
                f"{n_asserts} behavioral assertions (regression + new-behavior)"
            ),
        }
    else:
        exec_chk = {
            "type": "exec_assert",
            "targets": [
                {
                    "path": t["path"],
                    "functions": list(t["functions"]),
                    "constants": list(t["constants"]),
                    "imports": list(t["imports"]),
                }
                for t in targets
            ],
            "asserts": asserts,
            "timeout": 15,
            "description": (
                f"function `{fn}` and its caller across "
                f"{len(targets)} files satisfy all {n_asserts} behavioral assertions"
            ),
        }

    return [
        exec_chk,
        {
            "type": "call_schema_valid",
            "description": "all tool calls match opencode schemas",
        },
    ]


def build_row(entry: dict, prompt: str) -> dict:
    sid = entry["id"]
    row: dict[str, Any] = {
        "id": sid,
        "version": "v1",
        "repo": repo_for(entry),
        "name": entry["name"],
        "category": "code_editing",
        "contract": "completion",
        "surface": "tools",
        "min_calls": 3,
        "difficulty": _difficulty(entry),
        "prompt": prompt,
        "checks": _checks_for_row(entry),
    }
    sig = entry.get("structural_signature")
    if sig:
        row["structural_signature"] = dict(sig)
    return row


# ---------------------------------------------------------------------------
# Spec rendering
# ---------------------------------------------------------------------------


SPEC_TEMPLATE = """\
# v1 #{sid} {name}

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **{difficulty}**
- leak_function_name: **{leak_flag}**
- structural_signature: `{signature_line}`

## Repo

`{repo}` - {repo_url_short}, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `{repo_submodule_path}`.

## Criterion (mechanical)

- Target function (primary): `{fn}` (plus in-file callees: {callee_list})
- Target file(s): {target_files_list} (pinned at `{pin_short}`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> {behavior_prose_blockquote}

## Ground truth (reference edit)

{reference_edit_blocks}

## Hidden truth table (graders only) (N = {n_asserts})

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
{assert_rows}

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> {discovery_scope}` hits across these probes. The manifest pins D in `[{discovery_min}, {discovery_max}]`:

{probe_rows}

- Union (D = {d}): {d_list}

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **{leak_flag}**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> {prompt_blockquote}

## Pass criteria (2 checks)

1. `exec_assert` ({target_files_list}) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**{shortest_path_min} tool calls** minimum: one `grep` / `bash` to locate the file{shortest_path_extra}, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

{misstep_rows}

## Fail modes

{fail_mode_rows}

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
"""


def _code_block(s: str) -> str:
    # Strip one leading / trailing newline for compact rendering, keep inner layout.
    return s.strip("\n")


def _table_row(i: int, a: dict) -> str:
    expr = a["expr"].replace("|", "\\|")
    setup_note = ""
    if a.get("setup"):
        setup_note = " _(with setup)_"
    return f"| {i + 1} | {a['kind']} | {a['misstep']} | `{expr}`{setup_note} |"


def _misstep_row(misstep: str, a: dict) -> str:
    expr = a["expr"].replace("|", "\\|")
    return f"- **{misstep}**: caught by `{expr}` (kind: {a['kind']})"


def _signature_line(entry: dict) -> str:
    sig = entry.get("structural_signature") or {}
    if not sig:
        return "_(none)_"
    return ", ".join(f"{k}={v!r}" for k, v in sig.items())


def _reference_edit_blocks(targets: list[dict]) -> str:
    """Render one or more reference-edit code blocks (one per target)."""
    chunks: list[str] = []
    for t in targets:
        old = _code_block(t["reference_edit"]["oldString"])
        new = _code_block(t["reference_edit"]["newString"])
        chunks.append(
            f"`{t['path']}` (oldString occurs exactly once in the baseline):\n"
            f"\n"
            f"```python\n# oldString\n{old}\n```\n"
            f"\n"
            f"```python\n# newString\n{new}\n```\n"
        )
    return "\n".join(chunks)


def render_spec(
    entry: dict,
    prompt: str,
    discovery: dict[str, list[str]],
    pin: str,
) -> str:
    targets = targets_of(entry)
    multi = len(targets) > 1
    fn = primary_function(entry)
    primary_callees = targets[0]["functions"][1:]
    callee_list = (
        ", ".join(f"`{c}`" for c in primary_callees) if primary_callees else "_(none)_"
    )
    target_files_list = ", ".join(f"`{t['path']}`" for t in targets)

    repo = repo_for(entry)
    repos = _load_v1_repos()
    repo_meta = repos.get(repo, {})
    repo_url = repo_meta.get("url", "")
    # Compact "owner/name" form, e.g. "psf/requests" or "encode/httpx".
    repo_url_short = (
        repo_url.removeprefix("https://github.com/").removesuffix(".git")
        if repo_url.startswith("https://github.com/")
        else repo_url or repo
    )
    repo_submodule_path = repo_meta.get("submodule_path", f"projects/v1/{repo}") + "/"
    discovery_scope = discovery_scope_for(repo) or "(repo root)"

    assert_rows = "\n".join(_table_row(i, a) for i, a in enumerate(entry["asserts"]))
    probe_rows = "\n".join(
        f"- `{p}` -> {', '.join(f'`{x}`' for x in hits) if hits else '_(no match)_'}"
        for p, hits in discovery["per_probe"]
    )
    d_list = ", ".join(f"`{x}`" for x in discovery["union"])

    misstep_rows = "\n".join(
        _misstep_row(a["misstep"], a) for a in entry["asserts"] if a["misstep"] != "none"
    )
    fail_mode_rows = "\n".join(f"- {m}" for m in entry.get("prompt_fail_modes", []))

    behavior_prose_blockquote = (entry.get("behavior_prose") or "").rstrip().replace("\n", "\n> ")
    prompt_blockquote = prompt.replace("\n", "\n> ")

    if multi:
        shortest_path_min = 4
        shortest_path_extra = (
            ", a second `grep`/`read` to locate the cross-file caller"
        )
    else:
        shortest_path_min = 3
        shortest_path_extra = ""

    return SPEC_TEMPLATE.format(
        sid=entry["id"],
        name=entry["name"],
        fn=fn,
        callee_list=callee_list,
        target_files_list=target_files_list,
        pin_short=pin,
        repo=repo,
        repo_url_short=repo_url_short,
        repo_submodule_path=repo_submodule_path,
        discovery_scope=discovery_scope,
        difficulty=_difficulty(entry),
        leak_flag=str(_leak_fn_flag(entry)).lower(),
        signature_line=_signature_line(entry),
        behavior_prose_blockquote=behavior_prose_blockquote,
        reference_edit_blocks=_reference_edit_blocks(targets),
        n_asserts=len(entry["asserts"]),
        assert_rows=assert_rows,
        discovery_min=DISCOVERY_MIN,
        discovery_max=DISCOVERY_MAX,
        probe_rows=probe_rows,
        d=len(discovery["union"]),
        d_list=d_list,
        prompt_blockquote=prompt_blockquote,
        misstep_rows=misstep_rows,
        fail_mode_rows=fail_mode_rows,
        shortest_path_min=shortest_path_min,
        shortest_path_extra=shortest_path_extra,
    )


# ---------------------------------------------------------------------------
# Authoring gates (Layer 0)
# ---------------------------------------------------------------------------


def authoring_gates(entry: dict, prompt: str, discovery: dict[str, list[str]]) -> list[str]:
    """Run Layer 0 gates. Return list of error strings (empty = pass)."""
    errors: list[str] = []
    sid = entry["id"]
    prefix = f"#{sid}"

    targets = targets_of(entry)
    difficulty = _difficulty(entry)
    leak_fn = _leak_fn_flag(entry)
    slug = repo_for(entry)

    # (1) Per-target anchor uniqueness + patched AST sanity.
    for ti, t in enumerate(targets):
        try:
            src = read_target_file(t["path"], slug)
        except FileNotFoundError as e:
            errors.append(f"{prefix}: target #{ti} {t['path']!r}: {e}")
            return errors
        old = t["reference_edit"]["oldString"]
        new = t["reference_edit"]["newString"]
        count = src.count(old)
        if count != 1:
            errors.append(
                f"{prefix}: target #{ti} {t['path']}: oldString occurs {count} times (expected 1)"
            )
            return errors
        patched = src.replace(old, new, 1)
        try:
            assert_ast_has_symbols(patched, t["functions"], t["constants"])
        except (SyntaxError, ValueError) as e:
            errors.append(f"{prefix}: target #{ti} {t['path']} fails AST check: {e}")
            return errors

    # (2) Assert classification.
    try:
        classify_asserts(entry["asserts"])
    except ValueError as e:
        errors.append(f"{prefix}: assert classification: {e}")

    # (3) Prompt must NOT name any target file path.
    for t in targets:
        file_basename = Path(t["path"]).name
        if file_basename in prompt:
            errors.append(f"{prefix}: prompt leaks filename {file_basename!r}")
        if t["path"] in prompt:
            errors.append(f"{prefix}: prompt leaks file path {t['path']!r}")

    # (4) D-gate.
    d = len(discovery["union"])
    if not (DISCOVERY_MIN <= d <= DISCOVERY_MAX):
        errors.append(
            f"{prefix}: discovery D={d} out of range [{DISCOVERY_MIN}, {DISCOVERY_MAX}]; "
            f"union = {discovery['union']}"
        )

    # (5) De-leak gates.
    # (5a) zero `assert ` substrings in prompt -- the truth table must NOT leak.
    n_assert = prompt.count("assert ")
    if n_assert > 0:
        errors.append(
            f"{prefix}: de-leak: prompt contains {n_assert} `assert ` substring(s); "
            f"the truth table is graders-only"
        )

    # (5b) function-name leak flag honoured.
    # Exempt functions on `is_new` targets: those are synthetic helpers the
    # agent must CREATE (not discover), so the prompt has to name them.
    primary = primary_function(entry)
    if leak_fn:
        if primary not in prompt:
            errors.append(
                f"{prefix}: leak_function_name=true but primary function {primary!r} not in prompt"
            )
    else:
        names_to_hide: list[str] = []
        for t in targets:
            if t.get("is_new"):
                continue
            names_to_hide.extend(t["functions"])
        for name in names_to_hide:
            if name and re.search(rf"\b{re.escape(name)}\b", prompt):
                errors.append(
                    f"{prefix}: leak_function_name=false but prompt names function {name!r}"
                )

    # (5c) hard-tier samples MUST touch >=2 distinct files.
    if difficulty == "hard":
        if len({t["path"] for t in targets}) < 2:
            errors.append(
                f"{prefix}: hard-tier requires >=2 distinct files in `targets`; got {len(targets)}"
            )

    # (5d) literal-coverage: exception classes verbatim.
    for exc in _exception_classes(entry["asserts"]):
        if exc not in prompt:
            errors.append(
                f"{prefix}: literal-coverage: exception class {exc!r} used in setup "
                f"but not named in prompt"
            )

    # (5e) literal-coverage: `'X' in str(...)` substrings verbatim.
    for sub in _substring_literals(entry["asserts"]):
        if sub not in prompt:
            errors.append(
                f"{prefix}: literal-coverage: required substring {sub!r} (asserted via "
                f"`{sub!r} in str(...)`) does not appear verbatim in prompt"
            )

    # (5f) literal-coverage: any manifest-declared `prompt_required_literals`.
    for lit in entry.get("prompt_required_literals") or []:
        if lit not in prompt:
            errors.append(
                f"{prefix}: literal-coverage: required literal {lit!r} not in prompt"
            )

    # (5g) no banned fuzz words.
    m = FUZZ_RE.search(prompt)
    if m:
        errors.append(f"{prefix}: de-leak: banned fuzz word found in prompt: {m.group(0)!r}")

    # (5h) behavior_prose is required (the de-leaked prompt depends on it).
    if not (entry.get("behavior_prose") or "").strip():
        errors.append(f"{prefix}: behavior_prose is required for de-leaked prompts")

    # (5j) Triple-uniqueness gate (Phase B.3 of the scaling plan):
    #      No two samples may share the same (template, scope_kind,
    #      answer_shape) triple. The free-form `unique_trait` is purely
    #      descriptive and does not contribute to uniqueness.
    #
    #      Grandfathered for existing samples with sid <= 60: #53, #59, #60
    #      pre-date the gate and all use the cross-file-contract triple
    #      (the empirical Pearson on those is fine because they discriminate
    #      via real cross-file pattern variation rather than via signature).
    #      The gate applies strictly to NEW samples (sid >= 61) so the +20
    #      httpx expansion is forced into structural diversity.
    if sid >= 61:
        sig = entry.get("structural_signature") or {}
        my_triple = (
            sig.get("template"),
            sig.get("scope_kind"),
            sig.get("answer_shape"),
        )
        if all(my_triple):
            try:
                manifest = load_manifest()
            except Exception:
                manifest = {"samples": []}
            for other in manifest.get("samples", []):
                if other.get("id") == sid:
                    continue
                osig = other.get("structural_signature") or {}
                other_triple = (
                    osig.get("template"),
                    osig.get("scope_kind"),
                    osig.get("answer_shape"),
                )
                if other_triple == my_triple:
                    errors.append(
                        f"{prefix}: triple-uniqueness gate: "
                        f"(template={my_triple[0]!r}, scope_kind={my_triple[1]!r}, "
                        f"answer_shape={my_triple[2]!r}) collides with sample "
                        f"#{other.get('id')} {other.get('name')!r}; "
                        f"vary at least one of the three axes"
                    )
                    break

    # (5i) Easy-tier authoring gate (Phase B.2 of the scaling plan):
    #      Easy samples must have >=2 AST branches in the primary target
    #      function AND >=1 non-no-change misstep in the assert list.
    #
    #      Grandfathered for existing samples with sid <= 60: those entries
    #      pre-date the gate, and #56 + #58 in particular have <2 branches.
    #      The gate applies strictly to NEW samples (sid >= 61) so the +20
    #      httpx expansion authors functions with enough behavioral surface
    #      to lightly trip qwen-class models (the easy-tier-floor finding
    #      from the pilot panel).
    if difficulty == "easy" and sid >= 61:
        primary = primary_function(entry)
        primary_target = targets[0]
        try:
            primary_src = read_target_file(primary_target["path"], slug)
            primary_tree = ast.parse(primary_src)
            fn_node = next(
                (
                    n for n in primary_tree.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == primary
                ),
                None,
            )
        except (FileNotFoundError, SyntaxError):
            fn_node = None
        if fn_node is None:
            errors.append(
                f"{prefix}: easy-tier gate: primary function {primary!r} not found "
                f"in {primary_target['path']}"
            )
        else:
            branches = sum(
                1 for n in ast.walk(fn_node)
                if isinstance(n, (ast.If, ast.While, ast.For, ast.Try, ast.With, ast.ExceptHandler))
            )
            if branches < 2:
                errors.append(
                    f"{prefix}: easy-tier gate: primary function {primary!r} has "
                    f"only {branches} AST branch(es); need >=2 "
                    f"(If/While/For/Try/With/ExceptHandler) to give the easy tier "
                    f"discriminating headroom"
                )
        non_nc_missteps = {
            a.get("misstep")
            for a in entry["asserts"]
            if a.get("misstep") not in (None, "none", "no-change")
        }
        if not non_nc_missteps:
            errors.append(
                f"{prefix}: easy-tier gate: assert list has no non-no-change misstep "
                f"tags; add at least one partial-edit / over-edit / syntax-error tag "
                f"so the truth table catches more than the do-nothing mutant"
            )

    return errors


# ---------------------------------------------------------------------------
# File rewrite helpers
# ---------------------------------------------------------------------------


def rewrite_specs(
    entries_with_meta: list[tuple[dict, str, dict]],
    pin: str,
    dry_run: bool,
) -> None:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    keep_paths = set()
    for entry, prompt, discovery in entries_with_meta:
        sid = entry["id"]
        name = entry["name"]
        spec_path = SPEC_DIR / f"{sid:03d}_{name}.md"
        content = render_spec(entry, prompt, discovery, pin)
        keep_paths.add(spec_path)
        if dry_run:
            print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(content)} bytes)")
        else:
            spec_path.write_text(content)
            print(f"  wrote {spec_path.relative_to(ROOT)} ({len(content)} bytes)")

    # Delete stale specs for ids in the editing range whose filename no longer matches.
    # The editing range covers 51..90 (51..60 in requests + 61..80 in httpx + 81..90
    # reserved). Match 0[5-8]_*.md to cover that range.
    ids_in_manifest = {e["id"] for e, _, _ in entries_with_meta}
    for stale in sorted(SPEC_DIR.glob("0[5-8]?_*.md")):
        try:
            stale_id = int(stale.name[:3])
        except ValueError:
            continue
        if stale_id not in ids_in_manifest:
            continue
        if stale in keep_paths:
            continue
        if dry_run:
            print(f"  [dry-run] would delete stale spec {stale.relative_to(ROOT)}")
        else:
            stale.unlink()
            print(f"  deleted stale spec {stale.relative_to(ROOT)}")


def rewrite_jsonl(
    entries_with_meta: list[tuple[dict, str, dict]],
    dry_run: bool,
) -> None:
    new_rows_by_id: dict[int, dict] = {
        entry["id"]: build_row(entry, prompt) for entry, prompt, _ in entries_with_meta
    }
    edit_ids = set(new_rows_by_id)

    out_lines: list[str] = []
    seen_ids: set[int] = set()
    existing = []
    if SAMPLES_JSONL.exists():
        existing = SAMPLES_JSONL.read_text().splitlines()

    for raw in existing:
        line = raw.rstrip("\n")
        if not line.strip():
            out_lines.append(line)
            continue
        s = json.loads(line)
        if s.get("id") in edit_ids:
            sid = s["id"]
            if sid in seen_ids:
                raise RuntimeError(f"duplicate row for id {sid} in samples_v1.jsonl")
            seen_ids.add(sid)
            out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))
        else:
            out_lines.append(line)

    # Append any manifest ids that don't yet have a row.
    for sid in sorted(edit_ids - seen_ids):
        out_lines.append(json.dumps(new_rows_by_id[sid], ensure_ascii=False))

    new_content = "\n".join(out_lines) + "\n"
    if dry_run:
        print(
            f"  [dry-run] would write {SAMPLES_JSONL.relative_to(ROOT)} "
            f"({len(new_content)} bytes, {len(out_lines)} rows)"
        )
        return
    SAMPLES_JSONL.write_text(new_content)
    print(
        f"  wrote {SAMPLES_JSONL.relative_to(ROOT)} "
        f"({len(new_content)} bytes, {len(out_lines)} rows)"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--id", type=int, action="append")
    args = p.parse_args()

    manifest = load_manifest()
    samples = manifest.get("samples", [])
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]
        missing = wanted - {s["id"] for s in samples}
        if missing:
            print(f"ERROR: manifest missing ids {sorted(missing)}", file=sys.stderr)
            return 2

    print("=" * 60)
    print("Running authoring gates")
    print("=" * 60)

    entries_with_meta: list[tuple[dict, str, dict]] = []
    any_error = False
    for entry in samples:
        sid = entry["id"]
        name = entry["name"]
        slug = repo_for(entry)

        # Compute discovery union + per-probe hits up front (needed for both gates and spec).
        per_probe: list[tuple[str, list[str]]] = []
        union: set[str] = set()
        try:
            for pat in entry["discovery_probes"]:
                hits = discovery_files([pat], slug)
                per_probe.append((pat, hits))
                union.update(hits)
        except RuntimeError as e:
            print(f"  FAIL #{sid} {name}: {e}", file=sys.stderr)
            any_error = True
            continue
        discovery = {"per_probe": per_probe, "union": sorted(union)}

        prompt = build_prompt(entry)
        errs = authoring_gates(entry, prompt, discovery)
        if errs:
            print(f"  FAIL #{sid} {name}")
            for e in errs:
                print(f"    - {e}")
            any_error = True
        else:
            print(f"  PASS #{sid} {name}  (D={len(discovery['union'])})")
            entries_with_meta.append((entry, prompt, discovery))

    if any_error:
        print()
        print("RESULT: FAIL (authoring gates rejected one or more samples)")
        return 1

    print()
    print("=" * 60)
    print("Writing spec files")
    print("=" * 60)
    rewrite_specs(entries_with_meta, pin_short(), args.dry_run)

    print()
    print("=" * 60)
    print("Rewriting data/samples_v1.jsonl")
    print("=" * 60)
    rewrite_jsonl(entries_with_meta, args.dry_run)

    print()
    print("=" * 60)
    if args.dry_run:
        print("RESULT: DRY-RUN OK (no files written)")
    else:
        print(f"RESULT: OK ({len(entries_with_meta)} samples regenerated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
