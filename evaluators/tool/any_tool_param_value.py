from evaluators import register


@register("any_tool_param_value")
def check(tools, texts, chk):
    name = chk["tool"]
    param = chk["param"]
    expected = chk["equals"]
    hits = [t for t in tools if t["name"] == name]
    if not hits:
        return False, f"no call to {name!r}"
    if any(t["input"].get(param) == expected for t in hits):
        return True, None
    vals = [t["input"].get(param) for t in hits]
    return False, f"{name}.{param} = {vals}, expected {expected!r}"
