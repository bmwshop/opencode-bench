from evaluators import register


@register("no_tool_param_value")
def check(tools, texts, chk):
    """Pass iff NO tool call has tool=name AND input[param]==equals.

    Symmetric to any_tool_param_value: where that one pins a positive value,
    this one forbids it. Useful for selectivity tests like "model must NOT
    load skill name=X" or "model must NOT pass --force=true to bash".
    """
    name = chk["tool"]
    param = chk["param"]
    forbidden = chk["equals"]
    for t in tools:
        if t["name"] != name:
            continue
        if t["input"].get(param) == forbidden:
            return False, (
                chk.get("description")
                or f"forbidden: found {name}.{param} == {forbidden!r}"
            )
    return True, None
