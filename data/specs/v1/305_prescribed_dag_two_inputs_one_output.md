# v1 #305 prescribed_dag_two_inputs_one_output

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `train.py` and return the value of `EMBEDDING_LR`.
> - Subagent 2: read `prepare.py` and return the value of `VOCAB_SIZE`.
> 
> After both return, write `combined.py` at the repo root containing exactly these two lines (and no others):
> 
>     EMBEDDING_LR = <value from subagent 1>
>     VOCAB_SIZE = <value from subagent 2>
> 
> Do not call `read`, `grep`, `glob`, or `bash` directly; only the subagents inspect files.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch both task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `any_tool_name` | parent writes combined.py |
| 5 | `file_regex` | EMBEDDING_LR = 0.6 |
| 6 | `file_regex` | VOCAB_SIZE = 8192 |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |
