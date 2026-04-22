"""
Shared helpers for recursive (subagent-aware) evaluators.

`_collect_recursive_tools(trace_path)` walks the parent `.jsonl` trace and any
`{stem}.subagent-{sid[-10:]}.json` sidecars emitted by `run.py:_capture_subagents`,
returning a depth-first pre-order flat list of every tool call made at any
layer. Top-level calls land at `depth=0`; subagent calls are spliced in right
after the `task` entry that invoked them. This list is a strict superset of
what `eval.extract()` returns for the parent trace.

Sentinel entries (`__subagent_missing__`, `__subagent_depth_cap__`) surface
instrumentation gaps. Count-based wrappers and `call_schema_valid` short-circuit
on sentinels via `_check_sentinels`; tool-inspection wrappers only rewrite the
failure message via `_recursive_reason`.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

# Must match run.py:MAX_SUBAGENT_DEPTH.
MAX_SUBAGENT_DEPTH = 8
_TASK_ID_RE = re.compile(r"^task_id:\s*(ses_\w+)", re.M)


@lru_cache(maxsize=64)
def _collect_recursive_tools(trace_path):
    """Flat depth-first pre-order list of tool-call entries across the parent
    trace and all reachable subagent sidecars.

    Each real entry: {name, input, output, step, depth, sid}.
    Sentinel entries: {name in {"__subagent_missing__", "__subagent_depth_cap__"},
                       sid, depth, parent_sid, input, output, step}.

    Cached per `trace_path` so a single sample's multiple recursive checks
    parse the sidecars once.
    """
    trace_path = Path(trace_path)
    out = []
    if not trace_path.exists():
        return out
    stem = trace_path.stem
    visited = set()

    def _walk_sidecar(sid, depth, parent_sid):
        if sid in visited:
            return
        visited.add(sid)
        if depth >= MAX_SUBAGENT_DEPTH:
            out.append({
                "name": "__subagent_depth_cap__",
                "sid": sid, "depth": depth, "parent_sid": parent_sid,
                "input": {}, "output": "", "step": 0,
            })
            return
        sidecar = trace_path.with_name(f"{stem}.subagent-{sid[-10:]}.json")
        if not sidecar.exists():
            out.append({
                "name": "__subagent_missing__",
                "sid": sid, "depth": depth, "parent_sid": parent_sid,
                "input": {}, "output": "", "step": 0,
            })
            return
        try:
            data = json.loads(sidecar.read_text())
        except (json.JSONDecodeError, OSError):
            out.append({
                "name": "__subagent_missing__",
                "sid": sid, "depth": depth, "parent_sid": parent_sid,
                "input": {}, "output": "", "step": 0,
            })
            return
        for msg in data.get("messages", []):
            for p in msg.get("parts", []):
                if p.get("type") != "tool":
                    continue
                state = p.get("state", {}) or {}
                entry = {
                    "name": p.get("tool", ""),
                    "input": state.get("input", {}) or {},
                    "output": state.get("output", "") or "",
                    "step": 0,
                    "depth": depth,
                    "sid": sid,
                }
                out.append(entry)
                if entry["name"] == "task":
                    m = _TASK_ID_RE.search(entry["output"])
                    if m:
                        _walk_sidecar(m.group(1), depth + 1, sid)

    step = 0
    for line in trace_path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "step_start":
            step += 1
            continue
        if evt.get("type") != "tool_use":
            continue
        part = evt.get("part", {}) or {}
        state = part.get("state", {}) or {}
        parent_sid = evt.get("sessionID", "")
        entry = {
            "name": part.get("tool", ""),
            "input": state.get("input", {}) or {},
            "output": state.get("output", "") or "",
            "step": step,
            "depth": 0,
            "sid": parent_sid,
        }
        out.append(entry)
        if entry["name"] == "task":
            m = _TASK_ID_RE.search(entry["output"])
            if m:
                _walk_sidecar(m.group(1), 1, parent_sid)

    return out


def _check_sentinels(tools):
    """If any `__subagent_*` sentinel is present in `tools`, return
    `(False, reason)` describing the first one. Return `None` otherwise.
    Used by count-based wrappers and `call_schema_valid` to refuse to score
    when capture is incomplete."""
    for t in tools:
        name = t.get("name", "")
        if name == "__subagent_missing__":
            return False, (
                f"subagent-missing at depth {t.get('depth','?')} "
                f"({t.get('sid','?')}, parent {t.get('parent_sid','?')}) "
                f"-- re-run capture"
            )
        if name == "__subagent_depth_cap__":
            return False, (
                f"subagent-depth-cap hit at depth {t.get('depth','?')} "
                f"({t.get('sid','?')})"
            )
    return None


def _recursive_reason(reason, tools):
    """For tool-inspection wrappers: when a sentinel is present, append an
    instrumentation-gap note to an otherwise generic failure reason. Called
    only on failures; pass-through when no sentinels."""
    s = _check_sentinels(tools)
    if s is None:
        return reason
    _, sentinel_reason = s
    if reason:
        return f"{reason}; {sentinel_reason}"
    return sentinel_reason


def _real_tools(tools):
    """Strip `__subagent_*` sentinel entries so count-based evaluators don't
    mistakenly inflate their count by treating sentinels as real calls."""
    return [t for t in tools if not t.get("name", "").startswith("__subagent_")]
