# v1 #323 prescribed_parallel_6_aspect

## Category

orchestration

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch six `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `src/requests/api.py` and list its 8 top-level functions.
> - Subagent 2: read `src/requests/auth.py` and list its 4 top-level classes.
> - Subagent 3: read `src/requests/hooks.py` and list its 2 top-level functions.
> - Subagent 4: read `src/requests/exceptions.py` and report the COUNT of top-level classes (it has 25).
> - Subagent 5: read `src/requests/_internal_utils.py` and list its 2 top-level functions.
> - Subagent 6: read `src/requests/structures.py` and list its 2 top-level classes.
> 
> After all six return, write `survey.md` at the repo root with six sections in the order above (`## api.py functions`, `## auth.py classes`, `## hooks.py functions`, `## exceptions.py count`, `## _internal_utils.py functions`, `## structures.py classes`). The exceptions section is a single line: `count: 25`.
> 
> Do not call `read`, `grep`, or `glob` directly. This sample probes opencode's parallel-dispatch ceiling -- 6 task calls in one turn.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch all 6 task subagents in one assistant turn -- this probes opencode's fan-out ceiling |
| 2 | `tool_call_count` | exactly 6 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | exceptions count section present |
| 5 | `file_regex` | exceptions count = 25 |
| 6 | `file_regex` | AuthBase listed |
| 7 | `file_regex` | CaseInsensitiveDict listed |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
