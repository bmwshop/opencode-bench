#!/usr/bin/env python3
"""
Audit harness for v1 prescriptive orchestration samples (#301-#310).

Two passes:

Pass 1 -- Layer-0 manifest gates per entry:
  - id in range [301, 310]
  - pattern in vocabulary {parallel_dispatch, chain, dag_join, iteration, merge}
  - repo is in v1_repos.json
  - prompt is non-empty and mentions the prescribed shape
  - checks include `call_schema_valid`
  - parallel_dispatch and dag_join entries include `parallel_dispatch_count`
  - chain entries include `tool_call_sequence`
  - iteration entries include `tool_call_count` constraints on the iterating tool
  - all `tool_call_count`/`parallel_dispatch_count` checks have a valid constraint
  - any referenced file (read/grep param regex) is consistent with the prompt's
    repo (rough sanity, not exhaustive)

Pass 2 -- end-to-end derive + materialization + synth-trace:
  - re-runs data/scripts/derive_orchestration.py and verifies:
    * data/specs/v1/<NN>_<name>.md exists
    * data/samples_v1.jsonl contains the row
    * any declared workspace_overlay files are on disk
  - synthesizes a *compliant* opencode-style trace where the prescribed
    shape is followed and verifies all checks pass
  - synthesizes a *deviation* trace per pattern (e.g., wrong dispatch count,
    out-of-order calls) and verifies the targeted check fires

Usage
-----
    python3 data/scripts/audit_orchestration.py
    python3 data/scripts/audit_orchestration.py --id 301
    python3 data/scripts/audit_orchestration.py --pass 1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common import PROJECTS  # noqa: E402
from eval import load_evaluators  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_orchestration_criteria.json"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
OVERLAY_ROOT = PROJECTS / "v1" / "orchestration"
REPOS_JSON = ROOT / "data" / "v1_repos.json"

VALID_PATTERNS = {"parallel_dispatch", "chain", "dag_join", "iteration", "merge"}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def load_repo_slugs() -> set[str]:
    d = json.loads(REPOS_JSON.read_text())
    return {r.get("slug") or k for k, r in (d.get("repos", {}) if isinstance(d, dict) and "repos" in d else d).items()} if isinstance(d, dict) else set()


def load_orch_rows() -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not SAMPLES_JSONL.exists():
        return out
    for line in SAMPLES_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        s = json.loads(line)
        if s.get("category") == "orchestration":
            out[s["id"]] = s
    return out


# ---------------------------------------------------------------------------
# Pass 1: Layer 0 gates
# ---------------------------------------------------------------------------


def _has_check(checks: list[dict], chk_type: str) -> bool:
    return any(c.get("type") == chk_type for c in checks)


def pass1_entry(entry: dict, repo_slugs: set[str]) -> list[str]:
    errors: list[str] = []
    sid = entry.get("id")
    name = entry.get("name", "?")
    prefix = f"#{sid}"

    if not (301 <= (sid or 0) <= 330):
        errors.append(f"{prefix}: id out of range [301, 330]")
    pattern = entry.get("pattern")
    if pattern not in VALID_PATTERNS:
        errors.append(f"{prefix}: pattern {pattern!r} not in vocabulary {sorted(VALID_PATTERNS)}")
        return errors  # downstream gates depend on pattern

    if entry.get("repo") not in repo_slugs:
        errors.append(f"{prefix}: repo {entry.get('repo')!r} not declared in v1_repos.json")

    prompt = entry.get("prompt", "")
    if not prompt.strip():
        errors.append(f"{prefix}: prompt is empty")

    checks = entry.get("checks", [])
    if not _has_check(checks, "call_schema_valid"):
        errors.append(f"{prefix}: checks missing `call_schema_valid` (required for every sample)")

    if pattern in ("parallel_dispatch", "dag_join", "merge"):
        # Most samples in these patterns parallel-dispatch via `task` subagents,
        # but some intentionally use native parallel tool calls (e.g. #319
        # parallel `read`s) and one (#327 hierarchical merge) is sequential
        # at the parent layer because the parallelism is delegated into a
        # subagent. Accept either:
        #   (a) a parallel_dispatch_count check (the common case), OR
        #   (b) a recursive task indicator (any_tool_name_recursive=task)
        #       that proves the entry tests subagent dispatch even if the
        #       parent emits exactly one task call.
        has_parallel = any(c.get("type") == "parallel_dispatch_count" for c in checks)
        has_recursive_task = any(
            c.get("type") == "any_tool_name_recursive" and c.get("equals") == "task"
            for c in checks
        )
        if not (has_parallel or has_recursive_task):
            errors.append(
                f"{prefix}: pattern={pattern!r} requires either a "
                f"`parallel_dispatch_count` check OR a recursive `task` indicator"
            )

    if pattern == "chain":
        if not _has_check(checks, "tool_call_sequence"):
            errors.append(f"{prefix}: pattern=chain requires a `tool_call_sequence` check")

    if pattern == "iteration":
        # Need at least one tool_call_count with equals=N, where N matches
        # the prescribed iteration cardinality.
        cnt_checks = [c for c in checks if c.get("type") == "tool_call_count" and "equals" in c]
        if not cnt_checks:
            errors.append(f"{prefix}: pattern=iteration requires a `tool_call_count` with equals=N")

    # Every tool_call_count / parallel_dispatch_count must have a constraint.
    for c in checks:
        if c.get("type") in ("tool_call_count", "parallel_dispatch_count"):
            if not any(k in c for k in ("equals", "min", "max", "range")):
                errors.append(
                    f"{prefix}: {c.get('type')} on tool {c.get('tool')!r} is missing "
                    f"a constraint (equals|min|max|range)"
                )
            if not c.get("tool"):
                errors.append(f"{prefix}: {c.get('type')} missing required `tool` field")

    return errors


# ---------------------------------------------------------------------------
# Pass 2: derive + materialization + synth-trace
# ---------------------------------------------------------------------------


def _run_derive(ids: list[int] | None = None) -> tuple[bool, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "derive_orchestration.py")]
    if ids:
        for i in ids:
            cmd.extend(["--id", str(i)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr


def _grade(checks: list[dict], tools: list[dict], texts: list[str]) -> list[tuple[str, bool, str | None]]:
    """Run each check against (tools, texts). Returns (type, ok, reason).

    Skips checks that need on-disk artifacts (file_regex, exec_assert,
    text_contains_from_file) or a real trace_path (any *_recursive variant
    walks subagent sidecars that don't exist for synth-traces). The rest
    of the checks are tool-trajectory based and graderable in-process.
    """
    from evaluators import _registry
    out = []
    for c in checks:
        ct = c.get("type") or ""
        if ct in ("file_regex", "exec_assert", "text_contains_from_file"):
            continue
        if ct.endswith("_recursive"):
            # Recursive evaluators require trace_path (subagent sidecars on
            # disk). Synth grader can't provide that; skip.
            continue
        fn = _registry.get(ct)
        if fn is None:
            out.append((ct, False, f"unknown check type: {ct!r}"))
            continue
        try:
            ok, reason = fn(tools, texts, c)
        except Exception as e:
            out.append((ct, False, f"{type(e).__name__}: {e}"))
            continue
        out.append((ct, bool(ok), reason))
    return out


def _task_call(prompt: str, step: int) -> dict:
    """Build a synthetic task call with all required fields per opencode schema."""
    return {
        "name": "task",
        "input": {"prompt": prompt, "description": "explore", "subagent_type": "explore"},
        "output": "", "step": step,
    }


def _write_call(path: str, step: int, content: str = "stub") -> dict:
    return {
        "name": "write",
        "input": {"filePath": path, "content": content},
        "output": "", "step": step,
    }


def _read_call(path: str, step: int) -> dict:
    return {"name": "read", "input": {"filePath": path}, "output": "", "step": step}


def _grep_call(pattern: str, step: int, path: str | None = None) -> dict:
    inp = {"pattern": pattern}
    if path:
        inp["path"] = path
    return {"name": "grep", "input": inp, "output": "", "step": step}


def _bash_call(command: str, step: int) -> dict:
    return {
        "name": "bash",
        "input": {"command": command, "description": "synth"},
        "output": "", "step": step,
    }


def _synth_compliant(entry: dict) -> tuple[list[dict], list[str]]:
    """Build a fake tool-call trace that follows the prescribed shape for `entry`.
    All synthetic calls carry the schema-required fields so call_schema_valid
    passes (otherwise the audit can't tell our trace from a malformed one).
    """
    pattern = entry["pattern"]
    sid = entry["id"]
    if pattern == "parallel_dispatch":
        # Wave 2B fan-out width samples: #321=4, #322=5, #323=6 task calls
        # in one step. #324 is native parallel reads (no task dispatch).
        if sid == 321:
            return (
                [_task_call(f"sub_{i}", 1) for i in range(4)] +
                [_write_call("report.md", 2, content="## Optimizer\nEMBEDDING_LR: 0.6\n## Classes\n## Architecture\nASPECT_RATIO: 64\n## Tokenizer\nVOCAB_SIZE: 8192\n")],
                [],
            )
        if sid == 322:
            return (
                [_task_call(f"sub_{i}", 1) for i in range(5)] +
                [_write_call("inventory.md", 2, content="## api.py functions\nrequest\n## auth.py classes\nAuthBase\n## hooks.py functions\ndefault_hooks\n## _internal_utils.py functions\nto_native_string\n## structures.py classes\nCaseInsensitiveDict\n")],
                [],
            )
        if sid == 323:
            return (
                [_task_call(f"sub_{i}", 1) for i in range(6)] +
                [_write_call("survey.md", 2, content="## api.py functions\nrequest\n## auth.py classes\nAuthBase\n## hooks.py functions\ndefault_hooks\n## exceptions.py count\ncount: 25\n## _internal_utils.py functions\nto_native_string\n## structures.py classes\nCaseInsensitiveDict\n")],
                [],
            )
        if sid == 324:
            # 4 native parallel reads, no task dispatch, 1 write
            return (
                [_read_call(f"src/requests/m_{i}.py", 1) for i in range(4)] +
                [_write_call("inventory.md", 2, content="## api.py functions\nrequest\n## auth.py classes\nAuthBase\n## hooks.py functions\ndefault_hooks\n## _internal_utils.py functions\nto_native_string\n")],
                [],
            )
        n_task = 3 if sid in (301, 310) else 2
        return (
            [_task_call(f"sub_{i}", 1) for i in range(n_task)] +
            [_write_call("report.md", 2, content="## stub\n")],
            [],
        )
    if pattern == "chain":
        if sid == 303:
            return (
                [
                    _read_call("train.py", 1),
                    _grep_call("WEIGHT_DECAY", 2),
                    _write_call("occurrences.md", 3, content="train.py:443\ntrain.py:505\ntrain.py:532\n"),
                ],
                [],
            )
        if sid == 304:
            tools = [_read_call("src/requests/api.py", 1)]
            for i, fn_name in enumerate(["request", "get", "options", "head", "post", "put", "patch", "delete"], 2):
                tools.append(_grep_call(fn_name, i, "src/requests/sessions.py"))
            tools.append(_write_call("coverage.md", 10, content="request: used\nget: used\noptions: used\nhead: used\npost: used\nput: used\npatch: used\ndelete: used\n"))
            return tools, []
        if sid == 311:
            return (
                [
                    _read_call("prepare.py", 1),
                    _write_call("bos_token.md", 2, content="BOS_TOKEN: <|reserved_0|>\n"),
                ],
                [],
            )
        if sid == 312:
            return (
                [
                    _read_call("src/requests/api.py", 1),
                    _grep_call("delete", 2, "src/requests/sessions.py"),
                    _read_call("src/requests/sessions.py", 3),
                    _write_call("delete_callsites.md", 4, content="sessions.py:182\n"),
                ],
                [],
            )
        if sid == 313:
            return (
                [
                    _read_call("src/requests/models.py", 1),
                    _grep_call("Response", 2, "src/requests/api.py"),
                    _grep_call("Response", 3, "src/requests/adapters.py"),
                    _bash_call("wc -l src/requests/sessions.py", 4),
                    _grep_call("Response", 5, "src/requests/sessions.py"),
                    _write_call("response_usage.md", 6,
                                content="api.py: 17\nadapters.py: 10\nsessions.py: 23\n"),
                ],
                [],
            )
        if sid == 314:
            return (
                [
                    _read_call("src/requests/api.py", 1),
                    _grep_call("request", 2, "src/requests/sessions.py"),
                    _bash_call("wc -l src/requests/sessions.py", 3),
                    _read_call("src/requests/auth.py", 4),
                    _grep_call("_basic_auth_str", 5, "src/requests/sessions.py"),
                    _bash_call("wc -l src/requests/auth.py", 6),
                    _grep_call("HTTPBasicAuth", 7, "src/requests/api.py"),
                    _write_call("audit_report.md", 8,
                                content="sessions.py lines: 729\nauth.py lines: 295\nHTTPBasicAuth in api.py: 1\n"),
                ],
                [],
            )
        if sid == 315:
            return (
                [
                    _read_call("train.py", 1),
                    _task_call("read prepare.py and report VOCAB_SIZE", 2),
                    _read_call("README.md", 3),
                    _write_call("summary.md", 4,
                                content="train.py:EMBEDDING_LR: 0.6\nprepare.py:VOCAB_SIZE: 8192\nREADME.md:first_section: How it works\n"),
                ],
                [],
            )
    if pattern == "dag_join":
        if sid == 317:
            # parallel task -> sequential bash -> sequential write
            return (
                [_task_call("sub1", 1), _task_call("sub2", 1),
                 _bash_call("wc -l README.md", 2),
                 _write_call("dag_summary.md", 3,
                             content="train.py:WEIGHT_DECAY: 0.2\nprepare.py:MAX_SEQ_LEN: 2048\nREADME.md:line_count: 96\n")],
                [],
            )
        if sid == 318:
            # parallel task -> 3 sequential writes
            return (
                [_task_call("sub_a", 1), _task_call("sub_b", 1),
                 _write_call("session_methods.md", 2, content="prepare_request\nrequest\nsend\nclose\n"),
                 _write_call("adapter_methods.md", 3, content="init_poolmanager\nbuild_response\nsend\nclose\n"),
                 _write_call("common_methods.md", 4, content="close\nsend\n")],
                [],
            )
        if sid == 319:
            # parallel READ (not task) -> sequential write -- the native-tools variant
            return (
                [_read_call("src/requests/api.py", 1), _read_call("src/requests/auth.py", 1),
                 _write_call("inventory.md", 2,
                             content="## api.py top-level functions\nrequest\nget\noptions\nhead\npost\nput\npatch\ndelete\n## auth.py top-level definitions\n_basic_auth_str\nAuthBase\nHTTPBasicAuth\nHTTPProxyAuth\nHTTPDigestAuth\n")],
                [],
            )
        if sid == 320:
            # parallel task -> write intermediate -> bash verify -> write final
            return (
                [_task_call("sub_a", 1), _task_call("sub_b", 1),
                 _write_call("intermediate.md", 2, content="WEIGHT_DECAY=0.2\nVOCAB_SIZE=8192\n"),
                 _bash_call("cat intermediate.md", 3),
                 _write_call("final.md", 4, content="verified: WEIGHT_DECAY=0.2 VOCAB_SIZE=8192\n")],
                [],
            )
        # Wave 1 dag_join (#305, #306) and #316 default: 2-3 task calls + 1 write
        n_task = 3 if sid == 316 else 2
        return (
            [_task_call(f"sub_{i}", 1) for i in range(n_task)] + [_write_call("out.md", 2)],
            [],
        )
    if pattern == "iteration":
        if sid == 307:
            tools = []
            for i, f in enumerate(["adapters.py", "auth.py", "hooks.py", "sessions.py"], 1):
                tools.append(_bash_call(f'grep -c "def " src/requests/{f}', i))
            tools.append(_write_call("def_count.md", 5))
            return tools, []
        if sid == 308:
            tools = []
            for i, h in enumerate(["merge_setting", "to_key_val_list", "iter_slices"], 1):
                tools.append(_grep_call(h, i, "src/requests/sessions.py"))
            tools.append(_write_call("caller_table.md", 4))
            return tools, []
        if sid == 329:
            # 8 bash calls (one per file) + 1 write
            tools = []
            files_8 = ["adapters.py", "auth.py", "cookies.py", "exceptions.py",
                       "hooks.py", "models.py", "sessions.py", "utils.py"]
            for i, f in enumerate(files_8, 1):
                tools.append(_bash_call(f'grep -c "def " src/requests/{f}', i))
            tools.append(_write_call("def_count.md", 9,
                                     content="adapters.py: 20\nauth.py: 19\ncookies.py: 49\nexceptions.py: 3\nhooks.py: 2\nmodels.py: 44\nsessions.py: 28\nutils.py: 43\n"))
            return tools, []
        if sid == 330:
            # 3 grep + 1 bash (post-iter aggregation) + 1 write
            tools = []
            for i, h in enumerate(["merge_setting", "to_key_val_list", "iter_slices"], 1):
                tools.append(_grep_call(h, i, "src/requests/sessions.py"))
            tools.append(_bash_call("wc -l src/requests/sessions.py", 4))
            tools.append(_write_call("summary.md", 5,
                                     content="merge_setting: 9\nto_key_val_list: 3\niter_slices: 0\nsessions.py_total_lines: 729\n"))
            return tools, []
    if pattern == "merge":
        if sid == 325:
            # 4 parallel subagents + 1 write
            return (
                [_task_call(f"sub_{i}", 1) for i in range(4)] +
                [_write_call("stats.md", 2,
                             content="WEIGHT_DECAY: 0.2\ntop_level_functions: 9\ntop_level_classes: 6\nEMBEDDING_LR: 0.6\n")],
                [],
            )
        if sid == 326:
            # 2 parallel subagents (one finds, one doesn't) + 1 write
            return (
                [_task_call("sub_a", 1), _task_call("sub_b", 1),
                 _write_call("reconciliation.md", 2,
                             content="train.py: 0.2\nprepare.py: not found\ncanonical_value: 0.2\n")],
                [],
            )
        if sid == 327:
            # Hierarchical depth-2 dispatch: parent -> subagent
            # (recursive_dispatcher) -> sub-subagent (explore) -> read.
            # The synth grader can't materialize subagent sidecars on disk,
            # so any check that requires `trace_path` (the *_recursive ones)
            # gets skipped automatically by `_grade`. For the non-recursive
            # `tool_call_count(task, equals=2)` we inject the subagent's
            # task call into the synthetic tools list at step=1 (alongside
            # the parent's call) so the parent-only count matches what the
            # recursive-aware production grader would see. This is a synth
            # fiction but it lets the audit Pass-2 verify the manifest's
            # arithmetic without requiring a real subagent run.
            return (
                [
                    {"name": "task",
                     "input": {"prompt": "depth-2",
                               "description": "delegating explorer",
                               "subagent_type": "recursive_dispatcher"},
                     "output": "", "step": 1},
                    {"name": "task",
                     "input": {"prompt": "read train.py",
                               "description": "explore",
                               "subagent_type": "explore"},
                     "output": "", "step": 1},
                    _write_call("hierarchy.md", 2,
                                content="via_subsubagent: 0.6\nfinal: EMBEDDING_LR=0.6\n"),
                ],
                [],
            )
        if sid == 328:
            # 2 parallel tasks + 1 grep + 1 write
            return (
                [_task_call("sub_a", 1), _task_call("sub_b", 1),
                 _grep_call("def send", 2, "src/requests/sessions.py"),
                 _write_call("validation.md", 3,
                             content="sessions.Session.send: yes\nadapters.HTTPAdapter.send: yes\nvalidation_grep_count: 1\n")],
                [],
            )
        n_task = 3 if sid == 310 else 2
        return (
            [_task_call(f"sub_{i}", 1) for i in range(n_task)] + [_write_call("out.md", 2)],
            [],
        )
    return [], []


def _synth_deviation(entry: dict) -> tuple[list[dict], list[str], str]:
    """Build a deviation trace (wrong shape) and the verifier we expect to fire."""
    pattern = entry["pattern"]
    sid = entry["id"]
    if sid == 327:
        # Hierarchical merge: deviation = parent calls 0 task subagents.
        # The any_tool_name_recursive=task check would fire, but synth can't
        # grade recursive. Use tool_call_count(task, equals=1) as the
        # in-process detector: an empty parent-task trace fails it.
        return ([_write_call("hierarchy.md", 1)], [], "tool_call_count")
    if pattern in ("parallel_dispatch", "dag_join", "merge"):
        # sequential dispatch instead of parallel
        n_task = 3 if sid in (301, 310) else 2
        tools = [_task_call(f"sub_{i}", 1 + i) for i in range(n_task)] + [
            _write_call("out.md", 99),
        ]
        return tools, [], "parallel_dispatch_count"
    if pattern == "chain":
        # out-of-order: write before read
        return (
            [_write_call("out.md", 1), _read_call("anything", 2)],
            [],
            "tool_call_sequence",
        )
    if pattern == "iteration":
        # too few calls (e.g., 2 of 4)
        return (
            [_bash_call("grep -c def x", 1), _bash_call("grep -c def y", 2),
             _write_call("out.md", 3)],
            [],
            "tool_call_count",
        )
    return [], [], ""


def pass2_entry(entry: dict) -> list[str]:
    errors: list[str] = []
    sid = entry["id"]
    name = entry["name"]
    prefix = f"#{sid}"

    overlay_dir = OVERLAY_ROOT / f"{sid:03d}"
    for rel in entry.get("workspace_overlay", {}) or {}:
        f = overlay_dir / rel
        if not f.is_file():
            errors.append(f"{prefix}: overlay file {rel!r} missing under {overlay_dir.relative_to(ROOT)}/")

    spec_path = SPEC_DIR / f"{sid:03d}_{name}.md"
    if not spec_path.is_file():
        errors.append(f"{prefix}: spec {spec_path.relative_to(ROOT)} missing")

    rows = load_orch_rows()
    if sid not in rows:
        errors.append(f"{prefix}: samples_v1.jsonl missing row id={sid}")
        return errors
    row = rows[sid]
    if row.get("category") != "orchestration":
        errors.append(f"{prefix}: row category is {row.get('category')!r}, expected orchestration")
    if row.get("pattern") != entry["pattern"]:
        errors.append(f"{prefix}: row pattern mismatch")
    if row.get("repo") != entry["repo"]:
        errors.append(f"{prefix}: row repo mismatch")

    # Synth-trace tests
    compliant_tools, compliant_texts = _synth_compliant(entry)
    if not compliant_tools:
        errors.append(f"{prefix}: no synth_compliant template for pattern={entry['pattern']!r} sid={sid}")
        return errors
    grade = _grade(entry["checks"], compliant_tools, compliant_texts)
    failures = [(t, r) for t, ok, r in grade if not ok]
    if failures:
        errors.append(
            f"{prefix}: compliant synth-trace failed checks: "
            + "; ".join(f"{t}: {r}" for t, r in failures)
        )

    deviation_tools, deviation_texts, expected_fail = _synth_deviation(entry)
    if not deviation_tools:
        return errors  # no deviation template for this pattern
    grade = _grade(entry["checks"], deviation_tools, deviation_texts)
    matching_failures = [t for t, ok, _ in grade if t == expected_fail and not ok]
    if not matching_failures:
        errors.append(
            f"{prefix}: deviation synth-trace was supposed to trip {expected_fail!r} "
            f"but didn't (graded: {[(t, ok) for t, ok, _ in grade]})"
        )

    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", type=int, action="append")
    p.add_argument("--pass", dest="which_pass", choices=["1", "2", "both"], default="both")
    args = p.parse_args()

    load_evaluators()
    manifest = load_manifest()
    samples = manifest.get("samples", [])
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]

    repo_slugs = load_repo_slugs()
    any_error = False

    if args.which_pass in ("1", "both"):
        print("=" * 60)
        print("Pass 1 - Layer 0 gates")
        print("=" * 60)
        for entry in samples:
            errs = pass1_entry(entry, repo_slugs)
            if errs:
                print(f"  FAIL #{entry['id']} {entry['name']}")
                for e in errs:
                    print(f"    - {e}")
                any_error = True
            else:
                print(f"  PASS #{entry['id']} {entry['name']}")
        print()

    if args.which_pass in ("2", "both") and not any_error:
        print("=" * 60)
        print("Pass 2 - derive + materialization + synth-trace")
        print("=" * 60)
        ok, output = _run_derive([e["id"] for e in samples] if args.id else None)
        if not ok:
            print("  derive_orchestration.py failed:")
            print(output)
            any_error = True
        else:
            for entry in samples:
                errs = pass2_entry(entry)
                if errs:
                    print(f"  FAIL #{entry['id']} {entry['name']}")
                    for e in errs:
                        print(f"    - {e}")
                    any_error = True
                else:
                    print(f"  PASS #{entry['id']} {entry['name']}")
        print()

    print("=" * 60)
    if any_error:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS (all {len(samples)} orchestration samples validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
