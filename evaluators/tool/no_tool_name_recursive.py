from evaluators import register
from evaluators._recursive import (
    _collect_recursive_tools,
    _check_sentinels,
    _real_tools,
)
from evaluators.tool.no_tool_name import check as _strict


@register("no_tool_name_recursive")
def check(tools, texts, chk, trace_path):
    # Asserting *absence* requires complete visibility into every layer, so
    # this wrapper short-circuits on sentinels the way count-based wrappers do
    # (unlike `any_tool_name_recursive`, where a parent-level hit can still
    # pass even if a subagent sidecar is missing).
    recursive_tools = _collect_recursive_tools(trace_path)
    sentinel = _check_sentinels(recursive_tools)
    if sentinel is not None:
        return sentinel
    return _strict(_real_tools(recursive_tools), texts, chk)
