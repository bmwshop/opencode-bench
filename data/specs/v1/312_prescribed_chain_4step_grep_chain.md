# v1 #312 prescribed_chain_4step_grep_chain

## Category

orchestration

## Pattern

`chain` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> Perform exactly these four steps, in this order, with no other tool calls:
> 
> 1. **Read** `src/requests/api.py` (this lets you confirm `delete` is one of the 8 top-level functions).
> 2. **Grep** for the literal string `delete` in `src/requests/sessions.py`.
> 3. **Read** `src/requests/sessions.py`.
> 4. **Write** `delete_callsites.md` at the repo root with one line per occurrence of `delete` found in step 2, formatted as `sessions.py:<line_number>` (sorted by line number ascending). Empty file is invalid; at least one occurrence is expected.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | calls in order: read, grep, read, write (4-step chain) |
| 2 | `tool_call_count` | exactly two read calls |
| 3 | `tool_call_count` | exactly one grep call |
| 4 | `tool_call_count` | exactly one write call |
| 5 | `any_tool_param_regex` | grep searches for delete |
| 6 | `file_regex` | at least one sessions.py:<line_number> entry |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model emits a strictly ordered multi-step plan, with each step's output (or implicit context) flowing to the next. The `tool_call_sequence` and `tool_call_count` verifiers pin both the order and the cardinality.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
