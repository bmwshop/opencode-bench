from evaluators import register
from evaluators._recursive import _collect_recursive_tools, _recursive_reason
from evaluators.tool.any_tool_param_value import check as _strict


@register("any_tool_param_value_recursive")
def check(tools, texts, chk, trace_path):
    recursive_tools = _collect_recursive_tools(trace_path)
    ok, reason = _strict(recursive_tools, texts, chk)
    if ok:
        return True, reason
    return False, _recursive_reason(reason, recursive_tools)
