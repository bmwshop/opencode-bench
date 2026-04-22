from evaluators import register
from evaluators._recursive import (
    _collect_recursive_tools,
    _check_sentinels,
    _real_tools,
)
from evaluators.tool.tool_count_score import check as _strict


@register("tool_count_score_recursive")
def check(tools, texts, chk, trace_path):
    recursive_tools = _collect_recursive_tools(trace_path)
    sentinel = _check_sentinels(recursive_tools)
    if sentinel is not None:
        return sentinel
    return _strict(_real_tools(recursive_tools), texts, chk)
