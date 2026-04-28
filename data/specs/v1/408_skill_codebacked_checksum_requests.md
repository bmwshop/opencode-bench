# v1 #408 skill_codebacked_checksum_requests

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **code-backed-checksum**
- scope_kind: **single-skill**
- answer_shape: **stdout-needles**
- unique_trait: compute-checksum code-backed skill on requests

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `compute-checksum`

`projects/v1/skills/408/.opencode/skills/compute-checksum/SKILL.md`:

```text
---
name: compute-checksum
description: SHA-256 checksum of a file. Use when asked to compute or report a checksum / hash of a file in the repo.
---

To compute the checksum of a file in this project:

1. Run the bundled checksum script: `scripts/checksum.py <relative-path-to-file>`
   (relative to this skill's base directory, which the `skill` tool reports back
   to you on load).

2. The script prints a line of the form `sha256=<64-hex-chars>` to stdout.
   Capture that line.

3. Report at minimum the first 6 characters of the hash to the user in your
   final reply (e.g. `3f4a8b...`).

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
```

`projects/v1/skills/408/.opencode/skills/compute-checksum/scripts/checksum.py`:

```python
#!/usr/bin/env python3
"""SHA-256 checksum script for the compute-checksum skill (sample #408).

For the bench's deterministic audit, the synthesizer mocks this script's
output; the script itself just computes a real sha256 against the repo file.
At the pinned `requests` commit, sha256(src/requests/utils.py) starts with
`3f4a8b` -- the audit's text_contains check looks for that prefix.

Usage: python checksum.py <relative-or-absolute-path-to-file>
"""
import hashlib
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: checksum.py <path>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    print(f"sha256={h}")


if __name__ == "__main__":
    main()
```


## Prompt

> Compute and report the checksum of `src/requests/utils.py` in your final reply.
> 
> The project ships a skill that bundles a checksum-computation script; use the skill.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model invoked bash to run the script |
| 4 | `any_tool_param_regex` | bash command runs checksum.py |
| 5 | `text_contains` | response includes the first 6 chars of the sha256 checksum (verified against the pinned requests commit) |
| 6 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Code-backed tier-A on requests. The script prints sha256 of a file, with deterministic output for the pinned commit (we hard-code the expected first-6-chars in the manifest; the synthesizer's bash output mocks the script returning that prefix). Tests reproducibility + skill-mediated tool composition.
