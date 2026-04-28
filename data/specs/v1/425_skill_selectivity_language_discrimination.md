# v1 #425 skill_selectivity_language_discrimination

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **selectivity-language**
- scope_kind: **multi-skill-workspace**
- answer_shape: **tool-presence-or-absence**
- unique_trait: two skills, one Python-specific one JS-specific; pick by file language

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

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Selectivity by file-language. Both skills do code review; only one is for the right language. Tests file-extension-aware selection.
