# v1 #316 prescribed_dag_3_input_one_output

## Category

orchestration

## Pattern

`dag_join` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch three `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `src/requests/api.py` and list all 8 top-level function names (`request`, `get`, `options`, `head`, `post`, `put`, `patch`, `delete`).
> - Subagent 2: read `src/requests/auth.py` and list the 4 top-level class names (one is `AuthBase`, three are concrete auth classes).
> - Subagent 3: read `src/requests/hooks.py` and list its 2 top-level function names.
> 
> After all three return, write `inventory.md` at the repo root with three sections:
> 
> ## api.py functions
> <one name per line, 8 names total>
> 
> ## auth.py classes
> <one name per line, 4 names total>
> 
> ## hooks.py functions
> <one name per line, 2 names total>
> 
> Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch all 3 task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 3 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | api.py section present |
| 5 | `file_regex` | auth.py section present |
| 6 | `file_regex` | hooks.py section present |
| 7 | `file_regex` | AuthBase listed |
| 8 | `file_regex` | default_hooks listed |
| 9 | `file_regex` | request fn listed |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests parallel reads of independent inputs converging into a single output artifact. Combines parallel dispatch with output aggregation.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
