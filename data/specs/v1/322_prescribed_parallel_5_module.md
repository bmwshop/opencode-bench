# v1 #322 prescribed_parallel_5_module

## Category

orchestration

## Pattern

`parallel_dispatch` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch five `task` subagents (`subagent_type=explore`) in parallel, each reading a different module of the requests source tree:
> 
> - Subagent 1: `src/requests/api.py` -- list its 8 top-level functions.
> - Subagent 2: `src/requests/auth.py` -- list its 4 top-level classes.
> - Subagent 3: `src/requests/hooks.py` -- list its 2 top-level functions.
> - Subagent 4: `src/requests/_internal_utils.py` -- list its 2 top-level functions.
> - Subagent 5: `src/requests/structures.py` -- list its 2 top-level classes.
> 
> After all five return, write `inventory.md` at the repo root with five sections, in this order: `## api.py functions`, `## auth.py classes`, `## hooks.py functions`, `## _internal_utils.py functions`, `## structures.py classes`. Each section lists one name per line.
> 
> Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (13 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch all 5 task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 5 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | api.py section present |
| 5 | `file_regex` | auth.py section present |
| 6 | `file_regex` | hooks.py section present |
| 7 | `file_regex` | _internal_utils.py section present |
| 8 | `file_regex` | structures.py section present |
| 9 | `file_regex` | AuthBase class listed |
| 10 | `file_regex` | default_hooks fn listed |
| 11 | `file_regex` | to_native_string fn listed |
| 12 | `file_regex` | CaseInsensitiveDict class listed |
| 13 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model dispatches multiple tool/subagent calls in a single assistant turn (parallel-dispatch behavior). The `parallel_dispatch_count` verifier requires the prescribed N calls to share one step_start/step_finish boundary.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
