# v1 #311 prescribed_chain_2step_lite

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Perform exactly these two steps, in this order, with no other tool calls:
> 
> 1. **Read** `prepare.py`.
> 2. **Write** `bos_token.md` at the repo root containing exactly one line:
> 
>     BOS_TOKEN: <value>
> 
> where `<value>` is the exact string assigned to `BOS_TOKEN` at module scope in `prepare.py`.
> 
> The expected `BOS_TOKEN` value is the literal string `<|reserved_0|>` (including the angle brackets, pipes, and underscore).

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_sequence` | calls must appear in order: read, write |
| 2 | `tool_call_count` | exactly one read |
| 3 | `tool_call_count` | exactly one write |
| 4 | `any_tool_param_regex` | read targets prepare.py |
| 5 | `file_regex` | BOS_TOKEN reported with correct value |
| 6 | `call_schema_valid` | all tool calls match opencode schemas |
