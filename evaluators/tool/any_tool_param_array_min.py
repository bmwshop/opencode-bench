from evaluators import register


@register("any_tool_param_array_min")
def check(tools, texts, chk):
    name = chk["tool"]
    param = chk["param"]
    minimum = chk["min"]
    hits = [t for t in tools if t["name"] == name]
    if not hits:
        return False, f"no call to {name!r}"
    for t in hits:
        val = t["input"].get(param)
        if isinstance(val, list) and len(val) >= minimum:
            return True, None
    return False, f"{name}.{param} has fewer than {minimum} items"
