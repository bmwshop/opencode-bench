# v1 #329 prescribed_iter_8_module_def_count

## Category

orchestration

## Pattern

`iteration` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> For each of these 8 files, run **one separate** `bash` command using `grep -c "def " <file>` to count `def ` occurrences:
> 
> 1. `src/requests/adapters.py`
> 2. `src/requests/auth.py`
> 3. `src/requests/cookies.py`
> 4. `src/requests/exceptions.py`
> 5. `src/requests/hooks.py`
> 6. `src/requests/models.py`
> 7. `src/requests/sessions.py`
> 8. `src/requests/utils.py`
> 
> Issue 8 separate bash calls (one per file, in this order). Then write `def_count.md` at the repo root with 8 lines, in the same order:
> 
>     src/requests/adapters.py: 20
>     src/requests/auth.py: 19
>     src/requests/cookies.py: 49
>     src/requests/exceptions.py: 3
>     src/requests/hooks.py: 2
>     src/requests/models.py: 44
>     src/requests/sessions.py: 28
>     src/requests/utils.py: 43
> 
> The expected counts are pinned above. No other tool calls (no `read`, no `grep`, no `glob`).

## Pass criteria (14 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_count` | exactly 8 bash calls (one per file) |
| 2 | `tool_call_count` | exactly 1 write |
| 3 | `tool_call_count` | no read calls |
| 4 | `tool_call_count` | no grep tool calls |
| 5 | `tool_call_count` | no glob calls |
| 6 | `file_regex` | adapters.py count = 20 |
| 7 | `file_regex` | auth.py count = 19 |
| 8 | `file_regex` | cookies.py count = 49 |
| 9 | `file_regex` | exceptions.py count = 3 |
| 10 | `file_regex` | hooks.py count = 2 |
| 11 | `file_regex` | models.py count = 44 |
| 12 | `file_regex` | sessions.py count = 28 |
| 13 | `file_regex` | utils.py count = 43 |
| 14 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests bounded for-each-over-prescribed-list behavior. The model must issue exactly N calls (one per item), in the specified order, then aggregate.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
