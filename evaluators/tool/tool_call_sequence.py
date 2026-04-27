"""
Verify a prescribed ordered sequence of tool calls appears in the trace.

`chk['sequence']` is a list of step descriptors. Each descriptor is either:
  - a string `"<tool_name>"` (matches any call to that tool), OR
  - a dict `{"tool": "<name>", "input_regex": "<re>", "input_field": "<key>"}`
    (matches a call to that tool whose input field matches the regex; the
    `input_field` defaults to "command" for bash, "pattern" for grep,
    "filePath" for read/edit/write, and `None` (any field) otherwise).

The check is satisfied if there exists an in-order subsequence of `tools`
where each prescribed step matches a distinct trace call. Intermediate
calls between prescribed steps are allowed by default (`strict_adjacent=False`).
Setting `strict_adjacent: true` disallows any non-matching call between
two consecutive prescribed steps.

When `trace_path` is supplied the sequence is checked across the recursive
trace (parent + subagents in DFS pre-order). Subagent calls are spliced in
right after the `task` entry that invoked them, so a sequence like
`[task, read, write]` correctly matches a parent that dispatches a task
subagent (which reads), then writes.
"""
import re

from evaluators import register


_DEFAULT_INPUT_FIELD = {
    "bash": "command",
    "grep": "pattern",
    "glob": "pattern",
    "read": "filePath",
    "edit": "filePath",
    "write": "filePath",
    "task": "prompt",
}


def _matches_step(call: dict, step: dict | str) -> bool:
    if isinstance(step, str):
        return call.get("name") == step
    if call.get("name") != step.get("tool"):
        return False
    rgx = step.get("input_regex")
    if rgx is None:
        return True
    field = step.get("input_field") or _DEFAULT_INPUT_FIELD.get(step["tool"])
    inp = call.get("input", {}) or {}
    if field is None:
        # fall back to scanning all input string values
        haystack = " ".join(str(v) for v in inp.values())
    else:
        haystack = str(inp.get(field, ""))
    return bool(re.search(rgx, haystack))


@register("tool_call_sequence")
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

    sequence = chk.get("sequence")
    if not sequence:
        return False, "tool_call_sequence: missing required `sequence` field"

    strict_adjacent = bool(chk.get("strict_adjacent", False))

    # Greedy matcher: walk tools in order; advance the sequence cursor whenever
    # the next prescribed step matches. Strict-adjacent mode requires that the
    # match position is exactly one past the previous match.
    cursor = 0
    last_match_idx = -1
    for i, call in enumerate(tools):
        if cursor >= len(sequence):
            break
        if _matches_step(call, sequence[cursor]):
            if strict_adjacent and last_match_idx >= 0 and i != last_match_idx + 1:
                return False, (
                    f"tool_call_sequence: strict_adjacent violated between step "
                    f"{cursor - 1} and step {cursor} (intermediate non-matching call)"
                )
            cursor += 1
            last_match_idx = i

    if cursor >= len(sequence):
        return True, None
    missing = sequence[cursor:]
    names_seen = [t.get("name") for t in tools]
    return False, (
        f"tool_call_sequence: matched {cursor}/{len(sequence)} prescribed steps; "
        f"missing {missing} (saw tools {names_seen})"
    )
