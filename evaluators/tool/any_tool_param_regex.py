import re
from evaluators import register


@register("any_tool_param_regex")
def check(tools, texts, chk):
    name = chk["tool"]
    param = chk["param"]
    pattern = chk["pattern"]
    hits = [t for t in tools if t["name"] == name]
    if not hits:
        return False, f"no call to {name!r}"
    if any(re.search(pattern, str(t["input"].get(param, ""))) for t in hits):
        return True, None
    desc = chk.get("description", f"{name}.{param} did not match /{pattern}/")
    return False, desc
