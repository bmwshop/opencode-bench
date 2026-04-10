from pathlib import Path
from evaluators import register


@register("file_exists")
def check(tools, texts, chk):
    root = Path(chk["_project_dir"])
    target = root / chk["path"]
    if target.exists():
        return True, None
    return False, f"file not found: {chk['path']}"
