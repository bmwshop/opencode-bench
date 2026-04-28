# v1 #430 skill_composition_three_skills

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **composition-3-skills**
- scope_kind: **multi-skill-invocation**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: three skills; aggregated output combines all three

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `validate-train`

`projects/v1/skills/430/.opencode/skills/validate-train/SKILL.md`:

```text
---
name: validate-train
description: Project validation workflow. Use when asked to validate or check this autoresearch project; runs the bundled validation script and reports its output code.
---

To validate this project:

1. Run the bundled validation script: `scripts/validate.py` (relative to this
   skill's base directory, which the `skill` tool reports back to you on load).

2. The script prints a single line of the form `VALID_<8-hex-chars>` to stdout.
   Capture that token.

3. Report the captured token verbatim to the user in your final reply.

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
```

`projects/v1/skills/430/.opencode/skills/validate-train/scripts/validate.py`:

```python
#!/usr/bin/env python3
"""Trivial validation script for the validate-train skill (sample #407).

Prints a single-line validation token. The token is hard-coded at the pinned
commit so the audit harness can verify the model's response includes it. In a
real validation script this would inspect repo state and emit a derived token;
here we keep it deterministic for the bench.
"""
print("VALID_a8c9f1e2")
```

### `count-imports`

`projects/v1/skills/430/.opencode/skills/count-imports/SKILL.md`:

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

`projects/v1/skills/430/.opencode/skills/count-imports/scripts/count_imports.py`:

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

### `review-flow`

`projects/v1/skills/430/.opencode/skills/review-flow/SKILL.md`:

```text
---
name: review-flow
description: Code review workflow for this repository. Use when the user asks to review a code file for outstanding TODOs and produce a review document.
---

When asked to review a code file in this project, follow these steps in order:

1. Read the target file using the `read` tool.
2. Count the TODO comments (lines containing the literal `TODO`) in the file.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

The `# Review:` heading and `## TODO Count:` subheading are required substrings; the
hidden grader checks for both. The basename should appear without any directory
prefix (e.g. `utils.py`, not `src/requests/utils.py`).
```


## Prompt

> Produce a `comprehensive_report.md` at the repo root that combines:
> 
> 1. The validation token of this `autoresearch` project (use the validate skill).
> 2. The number of imports in `train.py` (use the count-imports skill).
> 3. A TODO-focused review of `train.py` (use the review skill).
> 
> Use all three relevant skills to gather the inputs.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | validate-train loaded |
| 2 | `any_tool_param_value_recursive` | count-imports loaded |
| 3 | `any_tool_param_value_recursive` | review-flow loaded |
| 4 | `min_tool_count` | at least 2 bash calls (validate.py + count_imports.py) |
| 5 | `file_regex` | report has Validation section |
| 6 | `file_regex` | report has Imports section |
| 7 | `file_regex` | report has Review section |
| 8 | `file_regex` | validation token referenced |
| 9 | `file_regex` | import count referenced |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Three-skill composition. Stress test for skill-load chaining and aggregation. Most demanding sample in the family.
