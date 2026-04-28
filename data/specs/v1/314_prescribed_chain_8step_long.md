# v1 #314 prescribed_chain_8step_long

## Category

orchestration

## Pattern

`chain` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> Perform exactly these eight steps, in this order, with no other tool calls:
> 
> 1. **Read** `src/requests/api.py`.
> 2. **Grep** for `request` in `src/requests/sessions.py`.
> 3. **Bash** `wc -l src/requests/sessions.py` (count lines).
> 4. **Read** `src/requests/auth.py`.
> 5. **Grep** for `_basic_auth_str` in `src/requests/sessions.py`.
> 6. **Bash** `wc -l src/requests/auth.py` (count lines).
> 7. **Grep** for `HTTPBasicAuth` in `src/requests/api.py`.
> 8. **Write** `audit_report.md` at the repo root with three lines:
> 
>     sessions.py lines: <value from step 3>
>     auth.py lines: <value from step 6>
>     HTTPBasicAuth in api.py: <count from step 7>

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | 8-step chain with mixed read/grep/bash/write |
| 2 | `tool_call_count` | exactly 2 read calls |
| 3 | `tool_call_count` | exactly 3 grep calls |
| 4 | `tool_call_count` | exactly 2 bash calls |
| 5 | `tool_call_count` | exactly 1 write |
| 6 | `file_regex` | sessions.py lines reported |
| 7 | `file_regex` | auth.py lines reported |
| 8 | `file_regex` | HTTPBasicAuth count reported |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model emits a strictly ordered multi-step plan, with each step's output (or implicit context) flowing to the next. The `tool_call_sequence` and `tool_call_count` verifiers pin both the order and the cardinality.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
