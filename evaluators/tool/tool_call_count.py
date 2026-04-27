"""
Count calls of a specific tool in the trace.

`chk` accepts:
  - `tool`: required, the tool name to count (e.g., "task", "bash", "write").
  - exactly one of:
      `equals: N`      - exactly N calls of `tool`
      `min: N`         - at least N calls
      `max: N`         - at most N calls
      `range: [lo, hi]` - lo..hi inclusive

When `trace_path` is supplied, calls made inside any `task` subagent are
counted alongside the parent's calls (recursive). Sentinel-aware: returns
False if subagent capture is incomplete (better to fail explicit than
silently over-count).
"""
from evaluators import register


@register("tool_call_count")
def check(tools, texts, chk, trace_path=None):
    if trace_path is not None:
        from evaluators._recursive import (
            _collect_recursive_tools, _check_sentinels, _real_tools,
        )
        recursive_tools = _collect_recursive_tools(trace_path)
        sentinel = _check_sentinels(recursive_tools)
        if sentinel is not None:
            return sentinel
        tools = _real_tools(recursive_tools)

    target = chk.get("tool")
    if not target:
        return False, "tool_call_count: missing required `tool` field"
    n = sum(1 for t in tools if t.get("name") == target)

    if "equals" in chk:
        want = int(chk["equals"])
        if n == want:
            return True, None
        return False, f"tool_call_count({target}): got {n}, want exactly {want}"
    if "min" in chk and "max" in chk:
        lo, hi = int(chk["min"]), int(chk["max"])
        if lo <= n <= hi:
            return True, None
        return False, f"tool_call_count({target}): got {n}, want {lo}..{hi}"
    if "min" in chk:
        lo = int(chk["min"])
        if n >= lo:
            return True, None
        return False, f"tool_call_count({target}): got {n}, want >= {lo}"
    if "max" in chk:
        hi = int(chk["max"])
        if n <= hi:
            return True, None
        return False, f"tool_call_count({target}): got {n}, want <= {hi}"
    if "range" in chk:
        lo, hi = int(chk["range"][0]), int(chk["range"][1])
        if lo <= n <= hi:
            return True, None
        return False, f"tool_call_count({target}): got {n}, want {lo}..{hi}"
    return False, "tool_call_count: missing constraint (equals|min|max|range)"
