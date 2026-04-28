# v1 #321 prescribed_parallel_4_facet

## Category

orchestration

## Pattern

`parallel_dispatch` (prescriptive)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch four `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent 1: read `train.py` and report `EMBEDDING_LR`, `UNEMBEDDING_LR`, `MATRIX_LR`, `WEIGHT_DECAY`.
> - Subagent 2: read `train.py` and list the names of the top-level classes (e.g., `GPTConfig`, `GPT`, etc.) in source-file order.
> - Subagent 3: read `train.py` and report `ASPECT_RATIO`, `HEAD_DIM`, `DEPTH`, `DEVICE_BATCH_SIZE`.
> - Subagent 4: read `prepare.py` and report `MAX_SEQ_LEN`, `VOCAB_SIZE`, `BOS_TOKEN`.
> 
> After all four return, write `report.md` at the repo root with four sections (`## Optimizer`, `## Classes`, `## Architecture`, `## Tokenizer`) populated from the subagent findings. Do not call `read`, `grep`, `glob`, or `bash` directly.

## Pass criteria (12 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch all 4 task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 4 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `any_tool_name` | parent writes report.md |
| 5 | `file_regex` | Optimizer section present |
| 6 | `file_regex` | Classes section present |
| 7 | `file_regex` | Architecture section present |
| 8 | `file_regex` | Tokenizer section present |
| 9 | `file_regex` | EMBEDDING_LR = 0.6 |
| 10 | `file_regex` | ASPECT_RATIO = 64 |
| 11 | `file_regex` | VOCAB_SIZE = 8192 |
| 12 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests whether the model dispatches multiple tool/subagent calls in a single assistant turn (parallel-dispatch behavior). The `parallel_dispatch_count` verifier requires the prescribed N calls to share one step_start/step_finish boundary.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
