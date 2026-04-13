from evaluators import register


@register("no_tool_any")
def check(tools, texts, chk):
    if len(tools) == 0:
        return True, None
    names = ", ".join(t["name"] for t in tools)
    return False, f"expected no tool calls, but got: {names}"
