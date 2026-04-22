from evaluators import register
from evaluators._recursive import (
    _collect_recursive_tools,
    _check_sentinels,
    _real_tools,
)
from evaluators.tool.no_tool_any import check as _strict


@register("no_tool_any_recursive")
def check(tools, texts, chk, trace_path):
    # Asserting "no tool calls anywhere" requires complete visibility, so short-
    # circuit on sentinels the same way `no_tool_name_recursive` does.
    recursive_tools = _collect_recursive_tools(trace_path)
    sentinel = _check_sentinels(recursive_tools)
    if sentinel is not None:
        return sentinel
    return _strict(_real_tools(recursive_tools), texts, chk)
