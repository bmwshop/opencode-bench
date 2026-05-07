# v1 #301 prescribed_parallel_3_facet_audit

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Audit this autoresearch repo. **In a single assistant turn**, dispatch three `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `train.py` and report the four optimizer learning-rate / weight-decay constants `EMBEDDING_LR`, `UNEMBEDDING_LR`, `MATRIX_LR`, `WEIGHT_DECAY`.
> - Subagent 2: read `train.py` and list the names of all top-level classes (e.g., `class GPTConfig`, `class GPT`, etc.), in source-file order.
> - Subagent 3: read `prepare.py` and report `MAX_SEQ_LEN`, `VOCAB_SIZE`, `BOS_TOKEN`.
> 
> After all three subagents return, write `report.md` at the repo root with three sections (`## Optimizer`, `## Classes`, `## Tokenizer`) populated from the subagent findings. Format inside each section: one line per item, `KEY: value` or just `<class_name>` for the classes list.
> 
> Do not call `read`, `grep`, `glob`, or `bash` directly; only the subagents inspect files.

## Pass criteria (12 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch all 3 task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 3 subagent dispatches, not more / fewer |
| 3 | `no_tool_name` | parent must not inspect files directly; only subagents read |
| 4 | `any_tool_name` | parent writes report.md |
| 5 | `file_regex` | report has Optimizer section |
| 6 | `file_regex` | report has Classes section |
| 7 | `file_regex` | report has Tokenizer section |
| 8 | `file_regex` | EMBEDDING_LR value 0.6 reported |
| 9 | `file_regex` | WEIGHT_DECAY value 0.2 reported |
| 10 | `file_regex` | VOCAB_SIZE value 8192 reported |
| 11 | `file_regex` | GPT class listed |
| 12 | `call_schema_valid` | all tool calls match opencode schemas |
