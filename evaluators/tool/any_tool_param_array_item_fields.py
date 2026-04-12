from evaluators import register


@register("any_tool_param_array_item_fields")
def check(tools, texts, chk):
    name = chk["tool"]
    param = chk["param"]
    fields = chk["fields"]
    hits = [t for t in tools if t["name"] == name]
    if not hits:
        return False, f"no call to {name!r}"
    for t in hits:
        val = t["input"].get(param)
        if not isinstance(val, list) or len(val) == 0:
            continue
        if all(isinstance(item, dict) and all(f in item for f in fields) for item in val):
            return True, None
    missing = ", ".join(repr(f) for f in fields)
    return False, f"{name}.{param} items missing required fields: {missing}"
