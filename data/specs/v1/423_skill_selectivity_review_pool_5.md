# v1 #423 skill_selectivity_review_pool_5

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **selectivity-pool-of-5**
- scope_kind: **multi-skill-workspace**
- answer_shape: **tool-presence-or-absence**
- unique_trait: 5 review-adjacent skills; only the most-specific one matches

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `todo-review`

`projects/v1/skills/423/.opencode/skills/todo-review/SKILL.md`:

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

### `python-code-review`

`projects/v1/skills/423/.opencode/skills/python-code-review/SKILL.md`:

```text
---
name: python-code-review
description: Generic Python code review covering structure, naming, docstrings, and idioms. Use for general code-quality reviews that are NOT focused on TODOs specifically.
---

For a generic Python code review:

1. Read the target file.
2. Identify structural concerns (long functions, unclear names, missing docstrings).
3. Write `code_review.md` at the repo root.

This skill is NOT focused on TODOs. For a TODO-focused review, use the
`todo-review` skill.
```

### `js-todo-review`

`projects/v1/skills/423/.opencode/skills/js-todo-review/SKILL.md`:

```text
---
name: js-todo-review
description: TODO-focused review for JavaScript / TypeScript files. Use when the target file is .js / .ts / .tsx and the user asks about outstanding TODOs.
---

When asked to review a JavaScript or TypeScript file's outstanding TODOs:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root.

This skill is for JS/TS files only. For Python TODO reviews, use the
`todo-review` skill instead.
```

### `style-check`

`projects/v1/skills/423/.opencode/skills/style-check/SKILL.md`:

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

### `comment-review`

`projects/v1/skills/423/.opencode/skills/comment-review/SKILL.md`:

```text
---
name: comment-review
description: Review of all kinds of comments in a code file (TODOs, FIXMEs, XXXs, license headers, docstrings). Use when the user asks for a comprehensive comment audit, NOT a TODO-only review.
---

For a comprehensive comment audit:

1. Read the target file.
2. Categorize all comments by type (TODO, FIXME, XXX, license, docstring, inline).
3. Write `comments.md` at the repo root.

This skill is NOT focused on TODOs only. For TODO-only reviews, use the
`todo-review` skill instead.
```


## Prompt

> Review `src/requests/auth.py` SPECIFICALLY for outstanding TODO comments and write a `review.md` summary at the repo root. The file is Python; the review should focus only on TODOs (not general code style or other comment kinds).
> 
> The project has multiple review-related skills installed; pick the one whose description matches a Python TODO-focused review precisely.

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model selected the most-specific review skill |
| 2 | `no_tool_param_value_recursive` | did not load the generic python code review |
| 3 | `no_tool_param_value_recursive` | did not load the wrong-language TODO review |
| 4 | `no_tool_param_value_recursive` | did not load style-check |
| 5 | `no_tool_param_value_recursive` | did not load comment-review |
| 6 | `any_tool_name` | skill loaded at parent layer |
| 7 | `any_tool_name` | model produced the review artifact |
| 8 | `file_regex` | review.md has the prescribed heading |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier D pool-of-5 selectivity. All 5 skills share review vocabulary; the user task is precise enough to demand 'todo-review' specifically. Tests precision-over-recall when the catalog is noisy. Authored after pilot showed #413's 3-skill pool was already discriminating; #423 raises the bar.
