# v1 #317 prescribed_dag_parallel_then_sequential

## Category

orchestration

## Pattern

`dag_join` (prescriptive)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Perform a DAG with a parallel front-end and a sequential back-end:
> 
> 1. **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
>    - Subagent A: read `train.py` and report the value of `WEIGHT_DECAY`.
>    - Subagent B: read `prepare.py` and report the value of `MAX_SEQ_LEN`.
> 
> 2. After both subagents return, run a single **bash** command: `wc -l README.md` (counts lines in README).
> 
> 3. **Write** `dag_summary.md` at the repo root with three lines:
> 
>     train.py:WEIGHT_DECAY: <value from subagent A>
>     prepare.py:MAX_SEQ_LEN: <value from subagent B>
>     README.md:line_count: <integer from bash output>
> 
> Expected values: WEIGHT_DECAY is 0.2, MAX_SEQ_LEN is 2048. Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch both subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `tool_call_count` | exactly 1 bash call (wc -l) |
| 4 | `tool_call_count` | exactly 1 write |
| 5 | `no_tool_name` | parent must not inspect files directly via read/grep/glob |
| 6 | `tool_call_sequence` | after the parallel dispatch, sequential bash then write |
| 7 | `file_regex` | WEIGHT_DECAY = 0.2 |
| 8 | `file_regex` | MAX_SEQ_LEN = 2048 |
| 9 | `file_regex` | line_count is an integer |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests parallel reads of independent inputs converging into a single output artifact. Combines parallel dispatch with output aggregation.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
