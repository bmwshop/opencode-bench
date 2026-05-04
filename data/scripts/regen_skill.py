#!/usr/bin/env python3
"""regen_skill: rewrite v1 SKILL family rows in `data/samples_v1.jsonl` from
`data/v1_skill_criteria.json`, and write/refresh the per-sample spec docs at
`data/specs/v1/<sid>_<name>.md`.

Authoring gates (run before the rewrite):

  G1 manifest schema           - every sample has id, name, repo, category=='skill',
                                 structural_signature{template, scope_kind,
                                 answer_shape}, skills_overlay[], prompt, checks[]
  G2 triple-uniqueness         - no two samples in the SKILL family share the
                                 (template, scope_kind, answer_shape) triple
  G3 skill-fixture-exists      - every skills_overlay[].fixture_path resolves to
                                 an actual file under projects/v1/skills/<sid>/
  G4 skill-frontmatter-valid   - each fixture parses as YAML+markdown with
                                 `name:` and `description:` keys
  G5 expected-invocation-checks - if `canonical_skill_access` is true, the
                                 manifest's checks include both:
                                  - any_tool_param_value(_recursive) skill.name
                                    matching at least one expected_skill_invocations
                                    entry where must_invoke is true
                                  - call_schema_valid
                                 and (if any expected entry has must_not_invoke=true)
                                 a no_tool_param_value_recursive guard for that name
  G6 repo-known                - sample.repo is registered in data/v1_repos.json

If any gate fails, the run aborts without touching samples_v1.jsonl. Pass --dry-run
to print what would change without writing.

Usage:
    python3 data/scripts/regen_skill.py
    python3 data/scripts/regen_skill.py --id 401
    python3 data/scripts/regen_skill.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import PROJECTS  # noqa: E402

MANIFEST = ROOT / "data" / "v1_skill_criteria.json"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"
SPEC_DIR = ROOT / "data" / "specs" / "v1"
SKILLS_DIR = PROJECTS / "v1" / "skills"
REPOS_JSON = ROOT / "data" / "v1_repos.json"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _load_repos() -> dict:
    if not REPOS_JSON.is_file():
        return {}
    return json.loads(REPOS_JSON.read_text())


def _read_skill_frontmatter(path: Path) -> dict | None:
    """Return the YAML frontmatter dict or None if not parseable."""
    if not path.is_file():
        return None
    text = path.read_text()
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if len(lines) < 2:
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm: dict = {}
    for line in lines[1:end]:
        m = re.match(r"^(\w+)\s*:\s*(.*?)\s*$", line)
        if m:
            fm[m.group(1)] = m.group(2)
    return fm


def authoring_gates(entry: dict, *, repos: dict, all_triples: dict) -> list[str]:
    """Run G1-G6 against one sample. Return list of error strings (empty == pass)."""
    sid = entry.get("id")
    prefix = f"#{sid}"
    errs: list[str] = []

    # G1 schema
    required = ["id", "name", "repo", "category", "structural_signature",
                "skills_overlay", "prompt", "checks"]
    for k in required:
        if k not in entry:
            errs.append(f"{prefix}: missing required field {k!r}")
    if entry.get("category") != "skill":
        errs.append(f"{prefix}: category must be 'skill', got {entry.get('category')!r}")
    sig = entry.get("structural_signature") or {}
    for k in ("template", "scope_kind", "answer_shape"):
        if not sig.get(k):
            errs.append(f"{prefix}: structural_signature missing or empty: {k}")
    if errs:
        return errs

    # G2 triple-uniqueness
    triple = (sig["template"], sig["scope_kind"], sig["answer_shape"])
    if triple in all_triples and all_triples[triple] != sid:
        errs.append(
            f"{prefix}: structural-signature triple {triple} collides with #{all_triples[triple]}; "
            f"vary at least one of (template, scope_kind, answer_shape)"
        )
    all_triples.setdefault(triple, sid)

    # G3 skill-fixture-exists
    sample_dir = SKILLS_DIR / f"{sid:03d}"
    for ovl in entry.get("skills_overlay", []) or []:
        fp = ovl.get("fixture_path")
        if not fp:
            errs.append(f"{prefix}: skills_overlay entry missing fixture_path")
            continue
        full = sample_dir / fp
        if not full.is_file():
            errs.append(f"{prefix}: fixture not found: {full.relative_to(ROOT)}")
            continue
        # G4 skill-frontmatter-valid (only for SKILL.md fixtures)
        if full.name == "SKILL.md":
            fm = _read_skill_frontmatter(full)
            if fm is None:
                errs.append(f"{prefix}: SKILL.md missing or has no parseable YAML frontmatter: {full.relative_to(ROOT)}")
            else:
                if not fm.get("name"):
                    errs.append(f"{prefix}: SKILL.md frontmatter missing 'name': {full.relative_to(ROOT)}")
                if not fm.get("description"):
                    errs.append(f"{prefix}: SKILL.md frontmatter missing 'description': {full.relative_to(ROOT)}")
                declared = ovl.get("skill_name")
                if declared and fm.get("name") and declared != fm["name"]:
                    errs.append(
                        f"{prefix}: skills_overlay.skill_name={declared!r} but SKILL.md frontmatter "
                        f"declares name={fm['name']!r} ({full.relative_to(ROOT)})"
                    )

    # G5 expected-invocation-checks
    if entry.get("canonical_skill_access"):
        check_types = [c.get("type") for c in entry.get("checks", [])]
        if "call_schema_valid" not in check_types:
            errs.append(f"{prefix}: canonical_skill_access requires a call_schema_valid check")
        # for each must_invoke skill, require an any_tool_param_value(_recursive) check
        skill_value_checks = [
            c for c in entry.get("checks", [])
            if c.get("type") in {"any_tool_param_value", "any_tool_param_value_recursive"}
            and c.get("tool") == "skill" and c.get("param") == "name"
        ]
        invoked_targets = {c.get("equals") for c in skill_value_checks}
        for inv in entry.get("expected_skill_invocations", []) or []:
            n = inv.get("skill_name")
            if inv.get("must_invoke") and n not in invoked_targets:
                errs.append(
                    f"{prefix}: expected_skill_invocations declares must_invoke {n!r} but no "
                    f"any_tool_param_value(_recursive) check pins skill.name=={n}"
                )
        # for each must_not_invoke, require EITHER a per-skill
        # no_tool_param_value(_recursive) guard OR a blanket
        # no_tool_name(_recursive) check that forbids every `skill` call
        # (the latter strictly subsumes the former for any skill name).
        no_value_checks = [
            c for c in entry.get("checks", [])
            if c.get("type") in {"no_tool_param_value", "no_tool_param_value_recursive"}
            and c.get("tool") == "skill" and c.get("param") == "name"
        ]
        forbidden_targets = {c.get("equals") for c in no_value_checks}
        # `no_tool_name(_recursive)` uses `not_equals` (singular or list).
        def _forbids_skill(check: dict) -> bool:
            if check.get("type") not in {"no_tool_name", "no_tool_name_recursive"}:
                return False
            ne = check.get("not_equals")
            if ne == "skill":
                return True
            if isinstance(ne, list) and "skill" in ne:
                return True
            return False
        forbids_all_skill = any(_forbids_skill(c) for c in entry.get("checks", []))
        for inv in entry.get("expected_skill_invocations", []) or []:
            n = inv.get("skill_name")
            if inv.get("must_not_invoke") and n not in forbidden_targets and not forbids_all_skill:
                errs.append(
                    f"{prefix}: expected_skill_invocations declares must_not_invoke {n!r} but no "
                    f"no_tool_param_value(_recursive) check forbids skill.name=={n} "
                    f"(and no blanket no_tool_name(_recursive) for `skill` either)"
                )

    # G6 repo-known
    if entry.get("repo") not in repos:
        errs.append(f"{prefix}: repo={entry.get('repo')!r} not registered in data/v1_repos.json")

    return errs


def build_jsonl_row(entry: dict) -> dict:
    """Project a manifest entry into the canonical JSONL shape consumed by run.py / eval.py."""
    return {
        "id": entry["id"],
        "version": "v1",
        "repo": entry["repo"],
        "name": entry["name"],
        "category": entry["category"],
        "contract": entry.get("contract", "completion"),
        "surface": entry.get("surface", "skills"),
        "min_calls": entry.get("min_calls"),
        "prompt": entry["prompt"],
        "checks": entry["checks"],
    }


def render_spec(entry: dict) -> str:
    sid = entry["id"]
    sig = entry["structural_signature"]
    # Build the skills-installed section: per skill, list every fixture file
    # under it AND embed any SKILL.md / Python script content inline so the
    # spec is self-contained (a reader doesn't have to click through to the
    # fixture tree to see what the skill actually says).
    by_skill: dict[str, list[str]] = {}
    for ovl in entry.get("skills_overlay", []):
        by_skill.setdefault(ovl["skill_name"], []).append(ovl["fixture_path"])
    sample_dir = SKILLS_DIR / f"{sid:03d}"
    skills_blocks: list[str] = []
    for skill_name, fixture_paths in by_skill.items():
        block_lines = [f"### `{skill_name}`", ""]
        for fp in fixture_paths:
            full = sample_dir / fp
            block_lines.append(f"`projects/v1/skills/{sid:03d}/{fp}`:")
            block_lines.append("")
            if full.is_file():
                content = full.read_text()
                # Use ```text fence for SKILL.md (markdown) so nested code
                # fences render; ```python for .py scripts.
                if full.suffix == ".py":
                    fence = "python"
                else:
                    fence = "text"
                block_lines.append(f"```{fence}")
                block_lines.append(content.rstrip())
                block_lines.append("```")
            else:
                block_lines.append(f"_(fixture missing: {fp})_")
            block_lines.append("")
        skills_blocks.append("\n".join(block_lines))
    skills_section = "\n".join(skills_blocks) if skills_blocks else "_(no skill fixtures listed)_"
    checks_table = "\n".join(
        f"| {i+1} | `{c.get('type')}` | {c.get('description', '-')} |"
        for i, c in enumerate(entry.get("checks", []))
    )
    cmp_blurb = ""
    if entry.get("comparison_id"):
        cmp_blurb = (
            f"\n## Comparison\n\n"
            f"This sample's parent is **#{entry['comparison_id']}** in the prescriptive "
            f"orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` "
            f"isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.\n"
        )
    notes = entry.get("_authoring_notes") or ""
    notes_block = f"\n## Authoring notes\n\n{notes}\n" if notes else ""
    return f"""# v1 #{sid} {entry['name']}

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **{sig['template']}**
- scope_kind: **{sig['scope_kind']}**
- answer_shape: **{sig['answer_shape']}**
- unique_trait: {sig.get('unique_trait', '-')}

## Repo

`{entry['repo']}` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

{skills_section}

## Prompt

> {entry['prompt'].replace(chr(10), chr(10) + '> ')}

## Pass criteria ({len(entry.get('checks', []))} checks)

| # | type | description |
|---|------|-------------|
{checks_table}
{cmp_blurb}
## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.
{notes_block}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, default=None,
                    help="If supplied, only regenerate the single sample with this id.")
    ap.add_argument("--dry-run", action="store_true", help="Don't write anything.")
    args = ap.parse_args()

    manifest = _load_manifest()
    repos = _load_repos()
    samples = manifest.get("samples", [])

    if args.id is not None:
        samples = [s for s in samples if s.get("id") == args.id]
        if not samples:
            print(f"no sample with id={args.id} in {MANIFEST}", file=sys.stderr)
            return 2

    print("=" * 60)
    print("Authoring gates")
    print("=" * 60)
    all_triples: dict[tuple, int] = {}
    any_error = False
    for entry in manifest.get("samples", []):
        # Run gates against the FULL manifest (so triple-uniqueness sees every sample)
        # but only filter the rewrite step below.
        errs = authoring_gates(entry, repos=repos, all_triples=all_triples)
        if errs:
            print(f"  FAIL #{entry.get('id')} {entry.get('name')}")
            for e in errs:
                print(f"    - {e}")
            any_error = True
        else:
            print(f"  PASS #{entry.get('id')} {entry.get('name')}")

    if any_error:
        print()
        print("RESULT: FAIL (authoring gates rejected one or more samples)")
        return 1

    # Read existing JSONL, drop SKILL family rows in scope, append rebuilt rows.
    if SAMPLES_JSONL.is_file():
        existing = [json.loads(l) for l in SAMPLES_JSONL.read_text().splitlines() if l.strip()]
    else:
        existing = []
    target_ids = {e["id"] for e in samples}
    kept = [r for r in existing if r["id"] not in target_ids]
    rebuilt = [build_jsonl_row(e) for e in samples]
    new_rows = kept + rebuilt
    new_rows.sort(key=lambda r: r["id"])

    print()
    print("=" * 60)
    print(f"Rewriting {SAMPLES_JSONL.relative_to(ROOT)}")
    print("=" * 60)
    if args.dry_run:
        print(f"  [dry-run] would write {len(new_rows)} rows ({len(rebuilt)} skill rows refreshed)")
    else:
        SAMPLES_JSONL.write_text("".join(json.dumps(r) + "\n" for r in new_rows))
        print(f"  wrote {SAMPLES_JSONL.relative_to(ROOT)} ({len(new_rows)} rows, "
              f"{len(rebuilt)} skill rows refreshed)")

    print()
    print("=" * 60)
    print(f"Refreshing specs in {SPEC_DIR.relative_to(ROOT)}")
    print("=" * 60)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    for entry in samples:
        sid = entry["id"]
        name = entry["name"]
        spec_path = SPEC_DIR / f"{sid:03d}_{name}.md"
        content = render_spec(entry)
        if args.dry_run:
            print(f"  [dry-run] would write {spec_path.relative_to(ROOT)} ({len(content)} bytes)")
        else:
            spec_path.write_text(content)
            print(f"  wrote {spec_path.relative_to(ROOT)} ({len(content)} bytes)")

    print()
    print("=" * 60)
    print(f"RESULT: OK ({len(rebuilt)} samples regenerated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
