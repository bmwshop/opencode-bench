"""
Detect parallel tool dispatch: count the maximum in-step calls of a given tool.

A "step" is a single assistant turn, delimited by `step_start`/`step_finish`
events in the opencode trace. When the model emits multiple `tool_use` events
between one `step_start` and the next `step_finish`, those tool calls are
considered to be dispatched in parallel (they're in the same assistant message).

This is the load-bearing signal for prescriptive parallel-dispatch samples
(#301, #302, #305, #306, #309, #310): the prompt prescribes "in one assistant
turn, dispatch N subagents". This evaluator checks that at least one step
indeed contains N (or matches another constraint) calls of the tool.

`chk` fields:
  - `tool`: required (typically "task" for subagent dispatch).
  - exactly one of `equals: N` | `min: N` | `max: N` | `range: [lo, hi]`.

Parent-layer only by design. Subagent tools collected via `_collect_recursive_tools`
all collapse to step=0, which would falsely report parallelism. The prescribed-
parallel-dispatch shape is a parent-side property (parent's assistant turn
contains multiple tool_use events), so we ignore the recursive variant here.
"""
from collections import Counter
from evaluators import register


@register("parallel_dispatch_count")
def check(tools, texts, chk, trace_path=None):
    target = chk.get("tool")
    if not target:
        return False, "parallel_dispatch_count: missing required `tool` field"

    # Group tools by step; only consider entries that have a step (parent layer).
    per_step: Counter = Counter()
    for t in tools:
        if t.get("name") == target:
            step = t.get("step")
            if step is None:
                continue
            per_step[step] += 1
    max_in_step = max(per_step.values()) if per_step else 0

    def _msg(tag):
        if not per_step:
            return f"parallel_dispatch_count({target}): no calls of {target!r} found"
        steps = sorted(per_step.items())
        breakdown = ", ".join(f"step{s}={n}" for s, n in steps)
        return f"parallel_dispatch_count({target}): max-in-step={max_in_step} ({breakdown}), {tag}"

    if "equals" in chk:
        want = int(chk["equals"])
        if max_in_step == want:
            return True, None
        return False, _msg(f"want exactly {want}")
    if "min" in chk and "max" in chk:
        lo, hi = int(chk["min"]), int(chk["max"])
        if lo <= max_in_step <= hi:
            return True, None
        return False, _msg(f"want {lo}..{hi}")
    if "min" in chk:
        lo = int(chk["min"])
        if max_in_step >= lo:
            return True, None
        return False, _msg(f"want >= {lo}")
    if "max" in chk:
        hi = int(chk["max"])
        if max_in_step <= hi:
            return True, None
        return False, _msg(f"want <= {hi}")
    if "range" in chk:
        lo, hi = int(chk["range"][0]), int(chk["range"][1])
        if lo <= max_in_step <= hi:
            return True, None
        return False, _msg(f"want {lo}..{hi}")
    return False, "parallel_dispatch_count: missing constraint (equals|min|max|range)"
