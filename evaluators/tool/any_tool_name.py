from evaluators import register


@register("any_tool_name")
def check(tools, texts, chk):
    expected = chk["equals"]
    if any(t["name"] == expected for t in tools):
        return True, None
    names = [t["name"] for t in tools]
    return False, f"no call to {expected!r} (got {names})"
