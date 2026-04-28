# v1 #326 prescribed_merge_with_disjoint_lookup

## Category

orchestration

## Pattern

`merge` (prescriptive)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel. They are asked the same question, but pointed at different files -- one of them will find the answer; the other will not:
> 
> - Subagent A: read `train.py` and report the value of the top-level constant `WEIGHT_DECAY`. (It should be 0.2.)
> - Subagent B: read `prepare.py` and report the value of the top-level constant `WEIGHT_DECAY`. (It does not exist in `prepare.py`; the subagent should say 'not found' or similar.)
> 
> After both return, write `reconciliation.md` at the repo root with exactly these three lines, reconciling the disjoint findings:
> 
>     train.py: 0.2
>     prepare.py: not found
>     canonical_value: 0.2
> 
> The canonical value is whichever of the two subagent answers is non-null. Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch both subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect files directly |
| 4 | `file_regex` | train.py reports 0.2 |
| 5 | `file_regex` | prepare.py reports not found |
| 6 | `file_regex` | parent reconciles to canonical_value 0.2 |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests subagent dispatch + reconciliation: multiple subagents return overlapping or related facts; the parent must merge them into a single deliverable.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
