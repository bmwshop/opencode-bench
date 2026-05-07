# v1 #413 skill_discovery_overlapping_descriptions

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `todo-review`

`projects/v1/skills/413/.opencode/skills/todo-review/SKILL.md`:

```text
---
name: todo-review
description: Code review focused specifically on outstanding TODO comments. Use when the user asks about TODOs, technical debt markers, or wants a review that itemizes deferred work.
---

When asked to review a file's outstanding TODO comments:

1. Read the target file using the `read` tool.
2. Count lines containing the literal `TODO` (case-sensitive).
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

This is the TODO-specific review workflow. For style-only reviews, use
`style-check`. For generic code-quality reviews not focused on TODOs, use
`code-review`.
```

### `code-review`

`projects/v1/skills/413/.opencode/skills/code-review/SKILL.md`:

```text
---
name: code-review
description: Generic code review for any Python file. Use for general analysis covering structure, complexity, and idiomatic style. NOT focused on TODOs specifically -- if the user asks about TODOs, use `todo-review` instead.
---

For a generic code review:

1. Read the target file.
2. Identify structural concerns (long functions, unclear names, missing docstrings).
3. Write `code_review.md` at the repo root summarizing the findings as prose.

This skill produces a generic prose review. It does NOT itemize TODO comments;
for that, use the `todo-review` skill (which is specifically for TODO-focused
analysis and produces a structured `review.md` with explicit TODO counting).
```

### `style-check`

`projects/v1/skills/413/.opencode/skills/style-check/SKILL.md`:

```text
---
name: style-check
description: Style-only review focused on formatting, naming, and PEP-8 conformance. Use when the user explicitly asks about formatting or style conventions; do NOT use for TODO-focused or generic code reviews.
---

For a style-only review:

1. Read the target file.
2. Identify PEP-8 / formatting issues (line length, naming, whitespace).
3. Write `style_review.md` at the repo root listing the formatting issues found.

This skill does NOT analyze logic or count TODOs. For TODO-focused reviews use
`todo-review`; for generic non-style reviews use `code-review`.
```


## Prompt

> Review `src/requests/models.py` for outstanding TODO comments and write a `review.md` summary at the repo root.
> 
> The project has multiple review-related skills installed; pick the one whose description specifically matches a TODO-focused review.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model selected todo-review (most specific match for a TODO-focused review) |
| 2 | `no_tool_param_value_recursive` | model did NOT load the generic code-review distractor |
| 3 | `no_tool_param_value_recursive` | model did NOT load the style-check distractor |
| 4 | `any_tool_name` | model used the skill tool at the parent layer |
| 5 | `any_tool_name` | model produced the review artifact |
| 6 | `file_regex` | review.md has the skill-prescribed heading |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |
