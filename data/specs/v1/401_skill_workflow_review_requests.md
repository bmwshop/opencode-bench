# v1 #401 skill_workflow_review_requests

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `review-flow`

`projects/v1/skills/401/.opencode/skills/review-flow/SKILL.md`:

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

> Review the file `src/requests/utils.py` for outstanding TODO comments and produce a `review.md` file at the repo root summarizing the findings.
> 
> The project ships a procedural skill that defines exactly how reviews should be done in this codebase. Use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer (not via subagent) |
| 3 | `tool_before` | skill loaded BEFORE the read it prescribes |
| 4 | `any_tool_name` | model produced an artifact |
| 5 | `file_regex` | review.md has the skill-prescribed heading |
| 6 | `file_regex` | review.md has the skill-prescribed TODO count subheading |
| 7 | `file_regex` | review.md mentions the target filename |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
