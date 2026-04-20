import re
from pathlib import Path
from evaluators import register


@register("text_contains_from_file")
def check(tools, texts, chk):
    root = Path(chk.get("_project_dir", ""))
    source = root / chk["source"]
    if not source.is_file():
        return False, f"source file not found: {chk['source']}"
    try:
        content = source.read_text()
    except Exception as e:
        return False, f"could not read {chk['source']}: {e}"
    m = re.search(chk["extract"], content, re.MULTILINE)
    if not m or not m.group(1):
        return False, f"extract pattern did not match in {chk['source']}"
    expected = m.group(1).strip()
    combined = " ".join(texts)
    if expected in combined:
        return True, None
    desc = chk.get("description", f"response text did not contain value from {chk['source']}")
    return False, desc
