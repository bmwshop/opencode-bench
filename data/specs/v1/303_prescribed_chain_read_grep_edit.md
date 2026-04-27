# v1 #303 prescribed_chain_read_grep_edit

## Category

orchestration

## Pattern

`chain` (prescriptive)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Perform exactly these three steps, in this order, with no other tool calls:
> 
> 1. **Read** `train.py` (use the `read` tool).
> 2. **Grep** for the literal string `WEIGHT_DECAY` in the autoresearch repo root (use the `grep` tool).
> 3. **Write** `occurrences.md` at the repo root, containing one line per match found in step 2, formatted as `<filepath>:<line_number>` (sorted by line number ascending).
> 
> Three occurrences of `WEIGHT_DECAY` exist in `train.py`. The output must list all three.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | calls must appear in order: read, grep, write |
| 2 | `tool_call_count` | exactly one read call |
| 3 | `tool_call_count` | exactly one grep call |
| 4 | `tool_call_count` | exactly one write call |
| 5 | `any_tool_param_regex` | read targets train.py |
| 6 | `any_tool_param_regex` | grep searches for WEIGHT_DECAY |
| 7 | `file_regex` | occurrence at train.py:443 listed |
| 8 | `file_regex` | occurrence at train.py:505 listed |
| 9 | `file_regex` | occurrence at train.py:532 listed |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model emits a strictly ordered multi-step plan, with each step's output (or implicit context) flowing to the next. The `tool_call_sequence` and `tool_call_count` verifiers pin both the order and the cardinality.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
