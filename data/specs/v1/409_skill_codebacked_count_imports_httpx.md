# v1 #409 skill_codebacked_count_imports_httpx

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **code-backed-count**
- scope_kind: **single-skill**
- answer_shape: **stdout-needles**
- unique_trait: count-imports code-backed skill on httpx

## Repo

`httpx` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `count-imports`

`projects/v1/skills/409/.opencode/skills/count-imports/SKILL.md`:

```text
---
name: count-imports
description: Count top-level import statements in a Python file. Use when asked how many imports a specific Python file contains.
---

To count the top-level imports in a Python file:

1. Run the bundled script: `scripts/count_imports.py <path-to-python-file>`
   (relative to this skill's base directory, which the `skill` tool reports back
   to you on load).

2. The script prints a line of the form `import_count=<integer>` to stdout.
   Capture that line.

3. Report the count to the user in your final reply, including the literal
   `import_count=<n>` substring (so downstream tooling can parse it).

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
```

`projects/v1/skills/409/.opencode/skills/count-imports/scripts/count_imports.py`:

```python
#!/usr/bin/env python3
"""Top-level import counter for the count-imports skill (sample #409).

Counts lines that start with `import ` or `from ` at column 0 (top-level imports).
At the pinned httpx commit, httpx/_utils.py has 7 such lines; the audit's
text_contains check looks for `import_count=7`.

Usage: python count_imports.py <path-to-python-file>
"""
import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: count_imports.py <path>", file=sys.stderr)
        sys.exit(2)
    pattern = re.compile(r"^(import|from)\s+", re.MULTILINE)
    with open(sys.argv[1]) as f:
        n = len(pattern.findall(f.read()))
    print(f"import_count={n}")


if __name__ == "__main__":
    main()
```


## Prompt

> Count the import statements in `httpx/_utils.py` and report the count in your final reply.
> 
> The project ships a skill that bundles a count-imports script; use the skill.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model invoked bash to run the script |
| 4 | `any_tool_param_regex` | bash command runs count_imports.py |
| 5 | `text_contains` | response reports the correct import_count |
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

Code-backed tier-A on httpx. Script counts `import` statements; expected count for httpx/_utils.py at the pinned commit is 7. Tests bash-with-arg + structured-output reporting.
