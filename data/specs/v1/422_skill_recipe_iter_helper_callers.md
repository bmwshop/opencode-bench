# v1 #422 skill_recipe_iter_helper_callers

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-iter-grep-foreach**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: for-each-helper grep via SKILL.md (sister of #308)

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

## Comparison

This sample's parent is **#308** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #308. Three helpers, one grep each. Skill prescribes the exact iteration shape.
