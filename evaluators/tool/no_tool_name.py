from evaluators import register


@register("no_tool_name")
def check(tools, texts, chk):
    bad = chk["not_equals"]
    if any(t["name"] == bad for t in tools):
        return False, f"should not call {bad!r} but did"
    return True, None
