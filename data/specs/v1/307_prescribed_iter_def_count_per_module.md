# v1 #307 prescribed_iter_def_count_per_module

## Category

orchestration

## Pattern

`iteration` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> For each of these 4 files in the requests source tree, run **one separate** `bash` command using `grep -c "def " <file>` to count the number of `def ` keyword occurrences:
> 
> 1. `src/requests/adapters.py`
> 2. `src/requests/auth.py`
> 3. `src/requests/hooks.py`
> 4. `src/requests/sessions.py`
> 
> Issue 4 separate `bash` calls (one per file, in this order). Then write `def_count.md` at the repo root with 4 lines, in the same order:
> 
>     src/requests/adapters.py: 20
>     src/requests/auth.py: 19
>     src/requests/hooks.py: 2
>     src/requests/sessions.py: 28
> 
> The expected counts are pinned above; your bash output should match. No other tool calls (no `read`, no `grep`, no `glob`).

## Pass criteria (14 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_count` | exactly 4 bash calls (one per file) |
| 2 | `tool_call_count` | exactly 1 write (def_count.md) |
| 3 | `tool_call_count` | no read calls |
| 4 | `tool_call_count` | no grep tool calls (must use bash grep) |
| 5 | `tool_call_count` | no glob calls |
| 6 | `any_tool_param_regex` | one bash call targets adapters.py |
| 7 | `any_tool_param_regex` | one bash call targets auth.py |
| 8 | `any_tool_param_regex` | one bash call targets hooks.py |
| 9 | `any_tool_param_regex` | one bash call targets sessions.py |
| 10 | `file_regex` | adapters.py count = 20 |
| 11 | `file_regex` | auth.py count = 19 |
| 12 | `file_regex` | hooks.py count = 2 |
| 13 | `file_regex` | sessions.py count = 28 |
| 14 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests bounded for-each-over-prescribed-list behavior. The model must issue exactly N calls (one per item), in the specified order, then aggregate.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
