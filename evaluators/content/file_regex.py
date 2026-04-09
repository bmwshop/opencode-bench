import re
from evaluators import register


@register("file_regex")
def check(tools, texts, chk):
    pattern = chk["pattern"]
    should = chk.get("should_match", True)
    content = ""
    for t in tools:
        if t["name"] in ("write", "edit"):
            fpath = t["input"].get("filePath", "")
            if chk.get("path") and chk["path"] in fpath:
                content += t["input"].get("content", "")
                content += t["input"].get("newString", "")
    if should:
        if not re.search(pattern, content):
            desc = chk.get("description", f"content did not match /{pattern}/")
            return False, desc
    else:
        if re.search(pattern, content):
            desc = chk.get("description", f"content unexpectedly matched /{pattern}/")
            return False, desc
    return True, None
