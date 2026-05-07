# v1 #320 prescribed_dag_with_intermediate_verification

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Perform a DAG with parallel reads, an intermediate write, a verification step, then a final write:
> 
> 1. **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
>    - Subagent A: read `train.py` and report `WEIGHT_DECAY`.
>    - Subagent B: read `prepare.py` and report `VOCAB_SIZE`.
> 
> 2. **Write** `intermediate.md` at the repo root with two lines:
> 
>     WEIGHT_DECAY=<value from subagent A>
>     VOCAB_SIZE=<value from subagent B>
> 
> 3. **Bash** `cat intermediate.md` (verification: re-emit the intermediate file's contents).
> 
> 4. **Write** `final.md` at the repo root with the line:
> 
>     verified: WEIGHT_DECAY=0.2 VOCAB_SIZE=8192
> 
> Expected values: WEIGHT_DECAY is 0.2, VOCAB_SIZE is 8192. Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch both subagents in one turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `tool_call_count` | exactly 2 writes (intermediate + final) |
| 4 | `tool_call_count` | exactly 1 bash (verification cat) |
| 5 | `no_tool_name` | parent must not inspect files directly |
| 6 | `tool_call_sequence` | DAG flow: parallel task -> write intermediate -> bash verify -> write final |
| 7 | `file_regex` | intermediate has WEIGHT_DECAY=0.2 |
| 8 | `file_regex` | intermediate has VOCAB_SIZE=8192 |
| 9 | `file_regex` | final.md has the verified line |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |
