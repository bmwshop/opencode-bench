# v1 #324 prescribed_parallel_4_native_reads

## Category

orchestration

## Pattern

`parallel_dispatch` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, issue four `read` calls in parallel (no subagents -- the parent reads four files directly in the same assistant turn):
> 
> - Read 1: `src/requests/api.py`.
> - Read 2: `src/requests/auth.py`.
> - Read 3: `src/requests/hooks.py`.
> - Read 4: `src/requests/_internal_utils.py`.
> 
> After all four reads return, write `inventory.md` at the repo root with four sections (`## api.py functions`, `## auth.py classes`, `## hooks.py functions`, `## _internal_utils.py functions`). Each section lists one name per line in source-file order.
> 
> Do not use `task`, `grep`, `glob`, or `bash`. Pairs with #319 (2 parallel reads) to test whether opencode's native-tool fan-out scales beyond 2.

## Pass criteria (11 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch all 4 reads in one assistant turn -- tests native-tool fan-out width |
| 2 | `tool_call_count` | exactly 4 reads |
| 3 | `tool_call_count` | exactly 1 write |
| 4 | `tool_call_count` | no subagent dispatches |
| 5 | `tool_call_count` | no grep |
| 6 | `tool_call_count` | no bash |
| 7 | `file_regex` | api.py section present |
| 8 | `file_regex` | auth.py section present |
| 9 | `file_regex` | AuthBase listed |
| 10 | `file_regex` | to_native_string listed |
| 11 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model dispatches multiple tool/subagent calls in a single assistant turn (parallel-dispatch behavior). The `parallel_dispatch_count` verifier requires the prescribed N calls to share one step_start/step_finish boundary.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
