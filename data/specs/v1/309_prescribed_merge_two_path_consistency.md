# v1 #309 prescribed_merge_two_path_consistency

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Verify that `train.py`'s `UNEMBEDDING_LR` value is consistent between its declaration and its use site. **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `train.py` and report the **declared** value of the top-level `UNEMBEDDING_LR` constant (the assignment `UNEMBEDDING_LR = ...` at module scope).
> - Subagent 2: read `train.py` and report the value passed as the keyword argument `unembedding_lr=` to the `MuonAdamW` optimizer constructor / `setup_optimizer` call (look around line 500).
> 
> After both return, write `consistency.md` at the repo root with exactly three lines:
> 
>     declared: <value from subagent 1>
>     used: <value from subagent 2>
>     agree: <yes if equal, no otherwise>
> 
> Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch both task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | declared value 0.004 |
| 5 | `file_regex` | used value 0.004 (or expression equal to 0.004) |
| 6 | `file_regex` | agree: yes |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |
