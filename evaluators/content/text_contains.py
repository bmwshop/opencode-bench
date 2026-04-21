import re
from evaluators import register


@register("text_contains")
def check(tools, texts, chk):
    pattern = chk["pattern"]
    combined = " ".join(texts)
    if re.search(pattern, combined, re.DOTALL | re.MULTILINE):
        return True, None
    desc = chk.get("description", f"response text did not match /{pattern}/")
    return False, desc
