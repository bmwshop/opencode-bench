# v1 #422 skill_recipe_iter_helper_callers

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `iter-helper-callers`

`projects/v1/skills/422/.opencode/skills/iter-helper-callers/SKILL.md`:

```text
---
name: iter-helper-callers
description: For-each-helper caller-count audit using grep. Use when the user asks to count callers of a list of helpers in a specific consumer file.
---

When asked to count callers of a list of helpers in a specific
consumer file:

1. For EACH helper name in the list, issue ONE separate `grep` call
   searching the consumer file for the helper name. Issue exactly N
   grep calls (one per helper), in the same order as the helper list.

2. After all grep calls return, write the report file (e.g.
   `caller_table.md`) at the repo root with N lines, in the same order:

   ```
   <helper_name>: <integer count>
   ```

Use the `grep` tool — exactly N times. No `bash`, no `read`, no `glob`.
```


## Prompt

> Compute caller counts in `src/requests/sessions.py` for these three helpers from `src/requests/utils.py`: `merge_setting`, `to_key_val_list`, `iter_slices`. Write the results to `caller_table.md` at the repo root.
> 
> The project ships a skill that defines the exact procedure (one separate grep call per helper); use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `min_tool_count` | at least 3 grep calls (one per helper) |
| 4 | `any_tool_name` | model produced caller_table.md |
| 5 | `file_regex` | merge_setting count = 9 |
| 6 | `file_regex` | to_key_val_list count = 3 |
| 7 | `file_regex` | iter_slices count = 0 |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
