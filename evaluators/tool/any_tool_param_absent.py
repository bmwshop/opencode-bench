from evaluators import register


@register("any_tool_param_absent")
def check(tools, texts, chk):
    name = chk["tool"]
    param = chk["param"]
    hits = [t for t in tools if t["name"] == name]
    if not hits:
        return True, None
    if any(param in t["input"] for t in hits):
        return False, f"{name} should not have param {param!r}"
    return True, None
