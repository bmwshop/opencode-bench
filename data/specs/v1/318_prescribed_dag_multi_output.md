# v1 #318 prescribed_dag_multi_output

## Category

orchestration

## Pattern

`dag_join` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent A: read `src/requests/sessions.py` and list the public method names of the `Session` class (don't start with `_`), one per line in source-file order.
> - Subagent B: read `src/requests/adapters.py` and list the public method names of the `HTTPAdapter` class, one per line in source-file order.
> 
> After both return, write THREE files at the repo root (in this order):
> 
> 1. `session_methods.md` — Subagent A's list verbatim, one method per line.
> 2. `adapter_methods.md` — Subagent B's list verbatim, one method per line.
> 3. `common_methods.md` — names that appear in both lists (intersection), sorted alphabetically, one per line.
> 
> The two classes share `send` and `close` at minimum; `common_methods.md` must include both. Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch both subagents in one turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `tool_call_count` | exactly 3 writes (one per output file) |
| 4 | `no_tool_name` | parent must not inspect files directly |
| 5 | `file_regex` | Session method prepare_request listed |
| 6 | `file_regex` | HTTPAdapter method init_poolmanager listed |
| 7 | `file_regex` | common_methods.md includes send |
| 8 | `file_regex` | common_methods.md includes close |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests parallel reads of independent inputs converging into a single output artifact. Combines parallel dispatch with output aggregation.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
