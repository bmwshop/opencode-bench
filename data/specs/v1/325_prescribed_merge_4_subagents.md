# v1 #325 prescribed_merge_4_subagents

## Category

orchestration

## Pattern

`merge` (prescriptive)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch four `task` subagents (`subagent_type=explore`) in parallel, each reporting a different statistic about `train.py`:
> 
> - Subagent 1: report the value of `WEIGHT_DECAY` (should be 0.2).
> - Subagent 2: count the top-level functions defined at module scope (should be 9, e.g. `norm`, `has_ve`, `apply_rotary_emb`, etc.).
> - Subagent 3: count the top-level classes (should be 6: `GPTConfig`, `CausalSelfAttention`, `MLP`, `Block`, `GPT`, `MuonAdamW`).
> - Subagent 4: report the value of `EMBEDDING_LR` (should be 0.6).
> 
> After all four return, write `stats.md` at the repo root with exactly these four lines:
> 
>     WEIGHT_DECAY: <subagent 1>
>     top_level_functions: <subagent 2>
>     top_level_classes: <subagent 3>
>     EMBEDDING_LR: <subagent 4>
> 
> Do not call `read`, `grep`, `glob`, or `bash` directly.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch all 4 subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 4 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | WEIGHT_DECAY = 0.2 |
| 5 | `file_regex` | EMBEDDING_LR = 0.6 |
| 6 | `file_regex` | 9 top-level functions |
| 7 | `file_regex` | 6 top-level classes |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests subagent dispatch + reconciliation: multiple subagents return overlapping or related facts; the parent must merge them into a single deliverable.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
