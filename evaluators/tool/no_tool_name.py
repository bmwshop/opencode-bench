from evaluators import register


@register("no_tool_name")
def check(tools, texts, chk):
    bad = chk["not_equals"]
    bad_set = {bad} if isinstance(bad, str) else set(bad)
    for t in tools:
        if t["name"] in bad_set:
            return False, f"should not call {t['name']!r} but did"
    return True, None
