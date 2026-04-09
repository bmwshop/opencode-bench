from evaluators import register


@register("min_tool_count")
def check(tools, texts, chk):
    name = chk["name"]
    minimum = chk["min"]
    count = sum(1 for t in tools if t["name"] == name)
    if count >= minimum:
        return True, None
    return False, f"expected >= {minimum} calls to {name!r}, got {count}"
