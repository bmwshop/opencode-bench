# v1 #306 prescribed_dag_response_attrs

## Category

orchestration

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `src/requests/models.py` and list the names of attributes assigned in `Response.__init__` (lines like `self.<name> = ...`), one per line in source-file order.
> - Subagent 2: read `src/requests/adapters.py` and find the `build_response` method of `HTTPAdapter`. List the names of attributes assigned to the local `response` variable in that method (lines like `response.<name> = ...`), one per line in source-file order.
> 
> After both return, write `attr_overlap.md` at the repo root with three sections:
> 
> ## __init__ attrs
> <sorted list, one per line>
> 
> ## build_response attrs
> <sorted list, one per line>
> 
> ## overlap
> <names that appear in both lists, sorted, one per line>
> 
> Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch both task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | report has __init__ attrs section |
| 5 | `file_regex` | report has build_response attrs section |
| 6 | `file_regex` | report has overlap section |
| 7 | `file_regex` | encoding attr listed (set in build_response) |
| 8 | `file_regex` | status_code attr listed (set in build_response) |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |
