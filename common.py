import json
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLES = ROOT / "data" / "samples.jsonl"
PROJECTS = ROOT / "projects"
RESULTS = ROOT / "results"
CAPTURES = ROOT / "captures"


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
