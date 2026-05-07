# v1 #427 skill_composition_validate_then_review

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `validate-train`

`projects/v1/skills/427/.opencode/skills/validate-train/SKILL.md`:

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

`projects/v1/skills/427/.opencode/skills/validate-train/scripts/validate.py`:

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

### `review-flow`

`projects/v1/skills/427/.opencode/skills/review-flow/SKILL.md`:

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

> First, validate the training pipeline of this `autoresearch` project (run the validation script and capture its token). Then write the validation output to `validation_output.md`, INCLUDING a `# TODO: investigate this token` line. Finally, perform a TODO-focused code review of `validation_output.md` and produce a `review.md` summary at the repo root.
> 
> The project ships skills for both the validation step and the review step; use both.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | validate-train skill loaded |
| 2 | `any_tool_param_value_recursive` | review-flow skill loaded |
| 3 | `any_tool_name` | model ran the validation script |
| 4 | `any_tool_name` | model produced the review artifact |
| 5 | `file_regex` | review.md has the prescribed heading |
| 6 | `file_regex` | review reports the 1 TODO |
| 7 | `file_regex` | review references the validation token |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
