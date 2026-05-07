# v1 #429 skill_composition_prose_chained

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `super-review`

`projects/v1/skills/429/.opencode/skills/super-review/SKILL.md`:

```text
---
name: super-review
description: Comprehensive code review skill that handles the full review workflow itself. Use when the user asks for a full code review and points to this skill specifically.
---

When asked to perform a comprehensive review:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

The review must include the `# Review:` heading and the `## TODO Count:`
subheading exactly as shown. This skill is self-contained and does not
require invoking other skills.
```


## Prompt

> Use the `super-review` skill to review `src/requests/auth.py` and write a `review.md` summary at the repo root.
> 
> Follow the skill's prescribed steps exactly, including any sub-skills it tells you to load.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | super-review skill loaded |
| 2 | `any_tool_name` | model produced the review artifact |
| 3 | `file_regex` | review.md has the prescribed heading |
| 4 | `file_regex` | review.md has the TODO Count subheading |
| 5 | `call_schema_valid` | all tool calls match opencode schemas |
