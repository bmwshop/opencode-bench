import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLES = ROOT / "data" / "samples.jsonl"
PROJECTS = ROOT / "projects"
RUNS = ROOT / "runs"


def model_slug(model):
    """Turn 'provider/model-name' into a filesystem-safe slug like 'provider_model-name'."""
    if not model:
        return "default"
    return re.sub(r"[/\\]+", "_", model)


def resolve_run(model=None, run=None):
    """Locate a run directory under runs/{model_slug}/{timestamp}/.

    Modes:
        model + run  -> exact: runs/{slug}/{run}/
        model only   -> latest timestamp under runs/{slug}/
        neither      -> latest timestamp across all runs/*/
    """
    if model and run:
        d = RUNS / model_slug(model) / run
        if not d.is_dir():
            return None
        return d

    if model:
        parent = RUNS / model_slug(model)
        return _latest_subdir(parent)

    if not RUNS.is_dir():
        return None
    best = None
    for model_dir in sorted(RUNS.iterdir()):
        if not model_dir.is_dir():
            continue
        candidate = _latest_subdir(model_dir)
        if candidate and (best is None or candidate.name > best.name):
            best = candidate
    return best


def _latest_subdir(parent):
    """Return the lexicographically last subdirectory (highest timestamp)."""
    if not parent.is_dir():
        return None
    dirs = sorted(
        (d for d in parent.iterdir() if d.is_dir()),
        key=lambda d: d.name,
    )
    return dirs[-1] if dirs else None


def list_runs():
    """Yield (model_slug, timestamp, meta_dict) for every run found."""
    if not RUNS.is_dir():
        return
    for model_dir in sorted(RUNS.iterdir()):
        if not model_dir.is_dir():
            continue
        for ts_dir in sorted(model_dir.iterdir()):
            if not ts_dir.is_dir():
                continue
            meta_path = ts_dir / "meta.json"
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            yield model_dir.name, ts_dir.name, meta


def load(args):
    with open(SAMPLES) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)
            if args.id and str(sample["id"]) not in args.id:
                continue
            if args.category and sample["category"] not in args.category:
                continue
            yield sample
