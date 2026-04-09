from evaluators import register


@register("any_tool_param_exists")
def check(tools, texts, chk):
    name = chk["tool"]
    param = chk["param"]
    hits = [t for t in tools if t["name"] == name]
    if not hits:
        return False, f"no call to {name!r}"
    if any(param in t["input"] for t in hits):
        return True, None
    return False, f"{name} missing param {param!r}"
