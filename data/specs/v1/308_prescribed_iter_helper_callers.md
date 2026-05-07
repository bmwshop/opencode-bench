# v1 #308 prescribed_iter_helper_callers

## Category

orchestration

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> For each of these 3 helper functions defined in `src/requests/utils.py`, count their callers in `src/requests/sessions.py` using **one separate** `grep` call per helper (3 grep calls total, in this order):
> 
> 1. `merge_setting`
> 2. `to_key_val_list`
> 3. `iter_slices`
> 
> Then write `caller_table.md` at the repo root with 3 lines, in the same order:
> 
>     merge_setting: 9
>     to_key_val_list: 3
>     iter_slices: 0
> 
> The expected counts are pinned above. No other tool calls (no `bash`, no `read`, no `glob`).

## Pass criteria (12 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_count` | exactly 3 grep calls (one per helper) |
| 2 | `tool_call_count` | exactly 1 write (caller_table.md) |
| 3 | `tool_call_count` | no bash calls |
| 4 | `tool_call_count` | no read calls |
| 5 | `tool_call_count` | no glob calls |
| 6 | `any_tool_param_regex` | one grep targets merge_setting |
| 7 | `any_tool_param_regex` | one grep targets to_key_val_list |
| 8 | `any_tool_param_regex` | one grep targets iter_slices |
| 9 | `file_regex` | merge_setting count = 9 |
| 10 | `file_regex` | to_key_val_list count = 3 |
| 11 | `file_regex` | iter_slices count = 0 |
| 12 | `call_schema_valid` | all tool calls match opencode schemas |
