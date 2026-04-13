from evaluators import register


@register("tool_count_score")
def check(tools, texts, chk):
    name = chk.get("name")
    optimal = chk["optimal"]
    limit = chk["limit"]
    count = sum(1 for t in tools if name is None or t["name"] == name)
    if count <= limit:
        return True, f"tool_calls={count} (optimal={optimal})"
    return False, f"tool_calls={count} exceeds limit={limit} (optimal={optimal})"
