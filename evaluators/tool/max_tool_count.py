from evaluators import register


@register("max_tool_count")
def check(tools, texts, chk):
    name = chk.get("name")
    maximum = chk["max"]
    count = sum(1 for t in tools if name is None or t["name"] == name)
    if count <= maximum:
        return True, None
    return False, f"expected <= {maximum} tool calls, got {count}"
