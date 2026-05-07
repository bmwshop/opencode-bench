# v1 #418 skill_recipe_chain_extract_check_report

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `chain-extract-check-report`

`projects/v1/skills/418/.opencode/skills/chain-extract-check-report/SKILL.md`:

```text
---
name: chain-extract-check-report
description: Extract-check-report workflow that audits whether each function from one file is referenced from another. Use for cross-module-coverage audits.
---

When asked to check whether each function in one file is referenced
from another:

1. **Read** the source file (e.g. `src/requests/api.py`) to identify
   the top-level function names.
2. For EACH identified function name, issue ONE separate `grep` call
   searching the consumer file (e.g. `src/requests/sessions.py`) for
   the function name. Issue exactly N grep calls (one per function),
   in the order the functions appear in the source.
3. Write `coverage.md` at the repo root with one line per function in
   the same order:

   ```
   <function_name>: used        (if grep returned >=1 match)
   <function_name>: unused      (otherwise)
   ```

No `glob` and no extra `read` calls beyond step 1.
```


## Prompt

> For each top-level function in `src/requests/api.py`, determine whether `src/requests/sessions.py` references it. Write the results to `coverage.md` at the repo root.
> 
> The project ships a skill that defines the exact procedure (which tools to call, in what order); use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `tool_before` | read precedes greps |
| 4 | `tool_before` | greps precede write |
| 5 | `file_regex` | request marked used |
| 6 | `file_regex` | get marked used |
| 7 | `file_regex` | delete marked used |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
