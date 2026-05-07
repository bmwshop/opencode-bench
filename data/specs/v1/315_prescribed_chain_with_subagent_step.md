# v1 #315 prescribed_chain_with_subagent_step

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Perform exactly these four steps, in this order, with no other tool calls beyond what's prescribed:
> 
> 1. **Read** `train.py` (parent reads directly).
> 2. **Dispatch a `task` subagent** (`subagent_type=explore`) and have it read `prepare.py` and report the value of `VOCAB_SIZE`. Wait for the subagent to return.
> 3. **Read** `README.md` (parent reads directly).
> 4. **Write** `summary.md` at the repo root with three lines:
> 
>     train.py:EMBEDDING_LR: <value from step 1>
>     prepare.py:VOCAB_SIZE: <value from subagent at step 2>
>     README.md:first_section: <text after "## " of the first level-2 heading from step 3>
> 
> Expected values: EMBEDDING_LR is 0.6, VOCAB_SIZE is 8192, first ## section is "How it works".

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | chain with task dispatch in the middle |
| 2 | `tool_call_count` | exactly 2 parent-level reads (subagent's reads excluded; the constraint is on parent's prescribed shape) |
| 3 | `tool_call_count` | exactly 1 subagent dispatch by the parent |
| 4 | `tool_call_count` | exactly 1 write by the parent |
| 5 | `file_regex` | EMBEDDING_LR = 0.6 |
| 6 | `file_regex` | VOCAB_SIZE = 8192 |
| 7 | `file_regex` | first README section is 'How it works' |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
