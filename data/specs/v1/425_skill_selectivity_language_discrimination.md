# v1 #425 skill_selectivity_language_discrimination

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `python-review`

`projects/v1/skills/425/.opencode/skills/python-review/SKILL.md`:

```text
---
name: python-review
description: Code review workflow for Python files. Use when the user asks to review a `.py` file for outstanding TODOs.
---

When asked to review a Python file:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this format:
   ```
   # Review: <basename>
   ## TODO Count: <integer>
   ## Issues
   <one bullet per TODO, or "No outstanding TODOs found.">
   ```

This skill is for Python files only. For JavaScript / TypeScript files,
use `javascript-review`.
```

### `javascript-review`

`projects/v1/skills/425/.opencode/skills/javascript-review/SKILL.md`:

```text
---
name: javascript-review
description: Code review workflow for JavaScript and TypeScript files. Use when the user asks to review a `.js`, `.ts`, `.tsx`, or `.jsx` file for outstanding TODOs.
---

When asked to review a JavaScript or TypeScript file:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this format:
   ```
   # Review: <basename>
   ## TODO Count: <integer>
   ## Issues
   <one bullet per TODO>
   ```

This skill is for JavaScript / TypeScript files only. For Python files,
use `python-review`.
```


## Prompt

> Review `src/requests/auth.py` for outstanding TODO comments and write a `review.md` summary at the repo root.
> 
> The project ships language-specific review skills; pick the one for the target file's language.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model selected the Python review skill |
| 2 | `no_tool_param_value_recursive` | did not load the JS review skill |
| 3 | `any_tool_name` | skill loaded at parent layer |
| 4 | `any_tool_name` | model produced the review artifact |
| 5 | `file_regex` | review.md has the prescribed heading |
| 6 | `call_schema_valid` | all tool calls match opencode schemas |
