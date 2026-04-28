# v1 #328 prescribed_merge_with_validation

## Category

orchestration

## Pattern

`merge` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch two `task` subagents (`subagent_type=explore`) in parallel:
> 
> - Subagent A: read `src/requests/sessions.py` and report whether the `Session` class has a method named `send` (yes/no).
> - Subagent B: read `src/requests/adapters.py` and report whether the `HTTPAdapter` class has a method named `send` (yes/no).
> 
> After both return, issue a single **grep** call: search `src/requests/sessions.py` for the literal `def send` (this is your validation step). Then write `validation.md` at the repo root with exactly three lines:
> 
>     sessions.Session.send: <yes/no from subagent A>
>     adapters.HTTPAdapter.send: <yes/no from subagent B>
>     validation_grep_count: <integer count of matches from grep>
> 
> Both subagents should answer 'yes' (both classes do have `send`). Do not call `read` or `glob` directly; the only parent-level non-task tool is the single grep validation call.

## Pass criteria (10 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch both subagents in one turn |
| 2 | `tool_call_count` | exactly 2 subagent dispatches |
| 3 | `tool_call_count` | exactly 1 validation grep |
| 4 | `tool_call_count` | exactly 1 write |
| 5 | `no_tool_name` | parent must not call read or glob directly |
| 6 | `any_tool_param_regex` | validation grep searches for `def send` |
| 7 | `file_regex` | Session.send: yes |
| 8 | `file_regex` | HTTPAdapter.send: yes |
| 9 | `file_regex` | grep count is reported |
| 10 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests subagent dispatch + reconciliation: multiple subagents return overlapping or related facts; the parent must merge them into a single deliverable.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
