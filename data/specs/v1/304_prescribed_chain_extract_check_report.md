# v1 #304 prescribed_chain_extract_check_report

## Category

orchestration

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> Perform these three steps in order:
> 
> 1. **Read** `src/requests/api.py` to identify the 8 top-level functions (`request`, `get`, `options`, `head`, `post`, `put`, `patch`, `delete`).
> 2. For each of those 8 function names, issue **one** `grep` call searching `src/requests/sessions.py` for the function name. Issue 8 grep calls total (one per name).
> 3. **Write** `coverage.md` at the repo root containing 8 lines, one per function, in this exact order: `request`, `get`, `options`, `head`, `post`, `put`, `patch`, `delete`. Each line must be `<function_name>: used` if the corresponding grep returned at least one match, or `<function_name>: unused` otherwise.
> 
> No other tool calls are permitted (in particular, no read calls beyond step 1, and no glob).

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | calls must include a read, then grep(s), then a write, in order |
| 2 | `tool_call_count` | exactly 1 read (api.py) |
| 3 | `tool_call_count` | exactly 8 grep calls (one per function) |
| 4 | `tool_call_count` | exactly 1 write (coverage.md) |
| 5 | `tool_call_count` | no glob calls |
| 6 | `any_tool_param_regex` | read targets api.py |
| 7 | `file_regex` | request marked used |
| 8 | `file_regex` | get marked used |
| 9 | `file_regex` | delete marked used |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |
