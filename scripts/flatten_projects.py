#!/usr/bin/env python3
"""
One-time migration: flatten projects/ to one directory per sample.

Before:
    projects/default/             <- shared by 17 samples
    projects/bash_only/           <- shared by 3 samples
    ...

After:
    projects/001/   projects/002/   ...   projects/033/

Each new dir is copied from the sample's current template, with every UUID in the
tree (and in the sample's JSON blob) replaced by a fresh uuid4. Samples in the same
template no longer share markers, so a leak from one sample does not contaminate
any other.

The script also strips the `project` field from samples.jsonl.

Run once from the repo root:
    python scripts/flatten_projects.py
"""

import json
import re
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
SAMPLES = ROOT / "data" / "samples.jsonl"

SKIP_DIRS = {"node_modules", "__pycache__", ".git"}

UUID_RE = re.compile(
    r"(?<![0-9a-fA-F-])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-fA-F-])"
)


def text_files(root):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            p.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue
        yield p


def find_uuids_in_tree(root):
    found = set()
    for p in text_files(root):
        found.update(UUID_RE.findall(p.read_text()))
    return found


def rewrite_tree(root, mapping):
    if not mapping:
        return
    for p in text_files(root):
        content = p.read_text()
        new = content
        for old, replacement in mapping.items():
            new = new.replace(old, replacement)
        if new != content:
            p.write_text(new)


def rewrite_string(s, mapping):
    for old, new in mapping.items():
        s = s.replace(old, new)
    return s


def main():
    samples = [json.loads(l) for l in SAMPLES.read_text().splitlines() if l.strip()]

    for s in samples:
        sid = s["id"]
        template = s.get("project", "default")
        src = PROJECTS / template
        dst = PROJECTS / f"{sid:03d}"
        if not src.is_dir():
            raise SystemExit(f"template projects/{template}/ missing for sample #{sid}")
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        blob = json.dumps(s)
        uuids = find_uuids_in_tree(dst) | set(UUID_RE.findall(blob))
        mapping = {old: str(uuid.uuid4()) for old in sorted(uuids)}

        rewrite_tree(dst, mapping)
        rewritten = json.loads(rewrite_string(blob, mapping))
        rewritten.pop("project", None)
        s.clear()
        s.update(rewritten)

        print(f"#{sid:03d} {s['name']:<22} {template:<20} -> projects/{sid:03d}/ ({len(mapping)} uuid{'s' if len(mapping) != 1 else ''})")

    with SAMPLES.open("w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    print(f"\nWrote {len(samples)} samples to {SAMPLES.relative_to(ROOT)}")
    print("Next: delete old template dirs, verify projects/NNN/ contents, then commit.")


if __name__ == "__main__":
    main()
