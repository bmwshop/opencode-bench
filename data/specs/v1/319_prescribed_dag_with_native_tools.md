# v1 #319 prescribed_dag_with_native_tools

## Category

orchestration

## Pattern

`dag_join` (prescriptive)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, issue two `read` calls in parallel (no subagents this time -- the parent reads both files directly in the same assistant turn):
> 
> - Read 1: `src/requests/api.py` (8 top-level functions).
> - Read 2: `src/requests/auth.py` (1 top-level function `_basic_auth_str` plus 4 classes).
> 
> After both reads return, write `inventory.md` at the repo root with two sections:
> 
> ## api.py top-level functions
> <one name per line, 8 functions: request, get, options, head, post, put, patch, delete>
> 
> ## auth.py top-level definitions
> <one name per line, 5 entries: _basic_auth_str (function), AuthBase, HTTPBasicAuth, HTTPProxyAuth, HTTPDigestAuth (classes)>
> 
> Do not use `task`, `grep`, `glob`, or `bash` -- only `read` (in parallel) and `write`.

## Pass criteria (11 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | step 1 must dispatch both reads in one assistant turn -- isolates whether parallel-dispatch works for native tools, not just task subagents |
| 2 | `tool_call_count` | exactly 2 reads |
| 3 | `tool_call_count` | exactly 1 write |
| 4 | `tool_call_count` | no subagent dispatches (this is the native-tools variant) |
| 5 | `tool_call_count` | no grep |
| 6 | `tool_call_count` | no bash |
| 7 | `file_regex` | api.py section present |
| 8 | `file_regex` | auth.py section present |
| 9 | `file_regex` | AuthBase listed |
| 10 | `file_regex` | HTTPBasicAuth listed |
| 11 | `call_schema_valid` | all tool calls match opencode schemas |

## Why this sample

Tests parallel reads of independent inputs converging into a single output artifact. Combines parallel dispatch with output aggregation.

## Notes

- Part of the v1 prescriptive orchestration batch (#301-#310). See `/Users/drekesh/.cursor/plans/v1_prescriptive_orchestration.plan.md` for the design.
- The graph shape and the artifact content are both verified. A model that produces a correct artifact via a non-prescribed shape (e.g., 2 task calls instead of 3) fails the prescribed-shape verifier.
