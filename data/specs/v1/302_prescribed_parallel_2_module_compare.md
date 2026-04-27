# v1 #302 prescribed_parallel_2_module_compare

## Category

orchestration

## Pattern

`parallel_dispatch` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `src/requests/sessions.py` and list the public method names of the `Session` class (i.e., methods on `Session` that don't start with `_`), in source-file order.
> - Subagent 2: read `src/requests/adapters.py` and list the public method names of the `HTTPAdapter` class (methods that don't start with `_`), in source-file order.
> 
> After both return, write `comparison.md` at the repo root with two sections:
> 
> ## Session
> <one method name per line>
> 
> ## HTTPAdapter
> <one method name per line>
> 
> Do not call `read`, `grep`, or `glob` directly; only the subagents inspect files.

## Pass criteria (11 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch both task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `any_tool_name` | parent writes comparison.md |
| 5 | `file_regex` | comparison has Session section |
| 6 | `file_regex` | comparison has HTTPAdapter section |
| 7 | `file_regex` | Session.prepare_request listed |
| 8 | `file_regex` | Session.merge_environment_settings listed |
| 9 | `file_regex` | HTTPAdapter.init_poolmanager listed |
| 10 | `file_regex` | HTTPAdapter.build_response listed |
| 11 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model dispatches multiple tool/subagent calls in a single assistant turn (parallel-dispatch behavior). The `parallel_dispatch_count` verifier requires the prescribed N calls to share one step_start/step_finish boundary.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
