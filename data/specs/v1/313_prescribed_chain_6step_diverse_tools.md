# v1 #313 prescribed_chain_6step_diverse_tools

## Category

orchestration

## Pattern

`chain` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> Perform exactly these six steps, in this order, with no other tool calls:
> 
> 1. **Read** `src/requests/models.py` (lists the `Response` class).
> 2. **Grep** for the literal `Response` in `src/requests/api.py`.
> 3. **Grep** for the literal `Response` in `src/requests/adapters.py`.
> 4. **Bash** `wc -l src/requests/sessions.py` (count lines in sessions.py).
> 5. **Grep** for the literal `Response` in `src/requests/sessions.py`.
> 6. **Write** `response_usage.md` at the repo root with three lines:
> 
>     api.py: <count from step 2>
>     adapters.py: <count from step 3>
>     sessions.py: <count from step 5>
> 
> The pinned counts are: `api.py: 17`, `adapters.py: 10`, `sessions.py: 23`.

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | 6-step chain with 4 distinct tool types in mixed order |
| 2 | `tool_call_count` | exactly 1 read |
| 3 | `tool_call_count` | exactly 3 grep calls (one per target file) |
| 4 | `tool_call_count` | exactly 1 bash call (wc -l) |
| 5 | `tool_call_count` | exactly 1 write |
| 6 | `file_regex` | api.py count = 17 |
| 7 | `file_regex` | adapters.py count = 10 |
| 8 | `file_regex` | sessions.py count = 23 |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model emits a strictly ordered multi-step plan, with each step's output (or implicit context) flowing to the next. The `tool_call_sequence` and `tool_call_count` verifiers pin both the order and the cardinality.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
