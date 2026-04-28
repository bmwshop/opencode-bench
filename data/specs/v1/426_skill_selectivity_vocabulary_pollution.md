# v1 #426 skill_selectivity_vocabulary_pollution

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **selectivity-vocab-pollution**
- scope_kind: **multi-skill-workspace**
- answer_shape: **tool-presence-or-absence**
- unique_trait: correct skill + 2 distractors that share the keyword 'code'

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `code-review`

`projects/v1/skills/426/.opencode/skills/code-review/SKILL.md`:

```text
---
name: code-review
description: Code-quality review focused on outstanding issues, TODOs, and structural concerns. Use when the user asks for a code review.
---

When asked to review a code file:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this format:
   ```
   # Review: <basename>
   ## TODO Count: <integer>
   ## Issues
   <one bullet per TODO, or "No outstanding TODOs found.">
   ```

This is the code-quality review skill. NOT for code formatting (use
`code-style-format`). NOT for test coverage (use `code-coverage-report`).
```

### `code-style-format`

`projects/v1/skills/426/.opencode/skills/code-style-format/SKILL.md`:

```text
---
name: code-style-format
description: Auto-format code per a style spec (black, prettier, etc.). Use ONLY when the user asks to reformat or apply a code style.
---

To apply code formatting, invoke the project's formatter via bash and report
diffs. This skill REWRITES files according to a style spec; it does NOT
audit for outstanding issues, TODOs, or structural problems.
```

### `code-coverage-report`

`projects/v1/skills/426/.opencode/skills/code-coverage-report/SKILL.md`:

```text
---
name: code-coverage-report
description: Generate a code-coverage report from the project's test suite. Use ONLY when the user asks for test-coverage statistics.
---

To generate a coverage report, invoke `pytest --cov` via bash and write the
result to `coverage_report.md`. This skill produces test-coverage statistics;
it does NOT review code for issues, TODOs, or structural problems.
```


## Prompt

> Review `src/requests/auth.py` (a code-quality review focused on outstanding issues) and write a `review.md` summary at the repo root.
> 
> The project has multiple 'code' skills installed; pick the one that matches a code-quality review.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model selected code-review |
| 2 | `no_tool_param_value_recursive` | did not load code-style-format |
| 3 | `no_tool_param_value_recursive` | did not load code-coverage-report |
| 4 | `any_tool_name` | skill loaded at parent layer |
| 5 | `any_tool_name` | model produced the review artifact |
| 6 | `file_regex` | review.md has the prescribed heading |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Vocabulary-pollution selectivity. All 3 skills start with 'code-'; descriptions disambiguate. Tests whether a model is anchored on shared vocabulary vs reading descriptions carefully.
