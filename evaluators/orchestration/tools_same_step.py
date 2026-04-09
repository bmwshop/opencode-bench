from evaluators import register


@register("tools_same_step")
def check(tools, texts, chk):
    name = chk["tool"]
    minimum = chk.get("min", 2)
    hits = [t["step"] for t in tools if t["name"] == name]
    if len(hits) < minimum:
        return False, f"expected >= {minimum} calls to {name!r}, got {len(hits)}"
    if len(set(hits[:minimum])) == 1:
        return True, None
    return False, f"first {minimum} {name!r} calls were in different steps: {hits[:minimum]}"
