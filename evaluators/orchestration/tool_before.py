from evaluators import register


@register("tool_before")
def check(tools, texts, chk):
    first = chk["first"]
    then = chk["then"]
    first_idx = next((i for i, t in enumerate(tools) if t["name"] == first), None)
    then_idx = next((i for i, t in enumerate(tools) if t["name"] == then), None)
    if first_idx is None:
        return False, f"no call to {first!r}"
    if then_idx is None:
        return False, f"no call to {then!r}"
    if first_idx < then_idx:
        return True, None
    return False, f"{first!r} (index {first_idx}) should come before {then!r} (index {then_idx})"
