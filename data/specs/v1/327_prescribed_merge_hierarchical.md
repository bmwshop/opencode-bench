# v1 #327 prescribed_merge_hierarchical

## Category

orchestration

## Pattern

`merge` (prescriptive)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> Dispatch one `task` subagent (`subagent_type=recursive_dispatcher`) with this exact instruction:
> 
> > Dispatch your OWN `task` subagent (`subagent_type=explore`) and ask it to read `train.py` and report the value of `EMBEDDING_LR`. Wait for your sub-subagent to return, then return its answer to me prefixed with `via_subsubagent: `.
> 
> After your subagent returns, write `hierarchy.md` at the repo root with exactly two lines:
> 
>     via_subsubagent: 0.6
>     final: EMBEDDING_LR=0.6
> 
> This tests opencode's recursive subagent dispatch: parent -> subagent (recursive_dispatcher, has task) -> sub-subagent (explore, reads train.py). Depth 2. Do not call `read`, `grep`, or `glob` directly. Notice that `subagent_type=recursive_dispatcher` is a custom subagent shipped with this sample's workspace overlay (`.opencode/agents/recursive_dispatcher.md`) -- the default `explore` subagent does not have the `task` tool.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `tool_call_count` | exactly 2 task calls in the recursive trace: parent's 1 + subagent's 1 (the depth-2 dispatch) |
| 2 | `any_tool_name_recursive` | at least one task call exists across the recursive trace |
| 3 | `any_tool_param_value_recursive` | parent's task uses subagent_type=recursive_dispatcher (the custom hierarchical-capable agent) |
| 4 | `any_tool_name_recursive` | the sub-subagent (explore) reads train.py |
| 5 | `no_tool_name` | parent must not inspect files directly |
| 6 | `file_regex` | value transited from sub-subagent through subagent to parent |
| 7 | `file_regex` | final line includes the value |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests subagent dispatch + reconciliation: multiple subagents return overlapping or related facts; the parent must merge them into a single deliverable.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
