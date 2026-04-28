# v1 #330 prescribed_iter_with_aggregation_step

## Category

orchestration

## Pattern

`iteration` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> Perform an iteration followed by an aggregation step:
> 
> 1. For each of these 3 helper functions defined in `src/requests/utils.py`, count their callers in `src/requests/sessions.py` using **one separate** `grep` call per helper (3 grep calls total, in this order):
>    - `merge_setting`
>    - `to_key_val_list`
>    - `iter_slices`
> 
> 2. After the 3 grep calls, run **one** `bash` command: `wc -l src/requests/sessions.py` (this is the post-iteration aggregation step -- it gathers a total-context number).
> 
> 3. Write `summary.md` at the repo root with exactly four lines:
> 
>     merge_setting: 9
>     to_key_val_list: 3
>     iter_slices: 0
>     sessions.py_total_lines: <integer from bash output>
> 
> No other tool calls. The expected helper counts are pinned above.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_count` | exactly 3 grep calls (one per helper) |
| 2 | `tool_call_count` | exactly 1 bash call (post-iteration aggregation: wc -l) |
| 3 | `tool_call_count` | exactly 1 write |
| 4 | `tool_call_count` | no read calls |
| 5 | `tool_call_sequence` | iteration steps then aggregation then write |
| 6 | `file_regex` | merge_setting count = 9 |
| 7 | `file_regex` | to_key_val_list count = 3 |
| 8 | `file_regex` | iter_slices count = 0 |
| 9 | `file_regex` | sessions.py total lines reported |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests bounded for-each-over-prescribed-list behavior. The model must issue exactly N calls (one per item), in the specified order, then aggregate.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
