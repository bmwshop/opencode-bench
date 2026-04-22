import re
from pathlib import Path
from evaluators import register


@register("file_regex_disk")
def check(tools, texts, chk):
    root = Path(chk.get("_project_dir", ""))
    target = root / chk["path"]
    if not target.is_file():
        desc = chk.get("description", f"file not found: {chk['path']}")
        return False, desc
    try:
        content = target.read_text()
    except Exception as e:
        return False, f"could not read {chk['path']}: {e}"
    pattern = chk["pattern"]
    should = chk.get("should_match", True)
    matched = re.search(pattern, content, re.MULTILINE) is not None
    if matched != should:
        fallback = (f"content did not match /{pattern}/" if should
                    else f"content unexpectedly matched /{pattern}/")
        return False, chk.get("description", fallback)
    return True, None
