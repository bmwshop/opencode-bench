# #8 direct_edit

## Category

efficiency

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool call efficiency -- performing a text replacement when all information is provided. When the prompt gives the exact file path, old string, and new string, the model should complete the task in as few tool calls as possible. This tests whether the model can identify the most direct path to the result.

## Design rationale

Many models have a learned "read first, then edit" pattern. This is often correct -- you need to see the file to know what to change. But when the prompt already supplies the exact old and new strings, a single `bash` call with `sed` accomplishes the task in one step. The `edit` tool, by contrast, requires a prior `read` (enforced at runtime by `filetime.assert`), making the minimum path with `edit` two calls.

The test is **tool-agnostic**: it does not require or forbid any specific tool. Instead it scores purely on call count via `tool_count_score`. This avoids conflicts with the `edit` tool's read-before-edit runtime enforcement -- the model can freely choose bash/sed (1 call, optimal) or read + edit (2 calls, acceptable).

| Strategy | Calls | Score |
|---|---|---|
| 1 bash call with `sed` | 1 | optimal |
| read + edit | 2 | acceptable (at limit) |
| read + edit + verify | 3+ | fail |

## Setup

Uses the default project. The file `src/utils.ts` contains `export const TOKEN = "abc123"`.

## Prompt

> In src/utils.ts, replace the exact string `abc123` with `xyz789`. Everything you need is in this message -- do it in a single step.

## Pass criteria (3 checks)

1. `max_tool_count` max 2 -- at most 2 tool calls
2. `tool_count_score` optimal 1, limit 2 -- 1 bash/sed call is optimal, 2 (read + edit) acceptable
3. `file_regex` `src/utils.ts` matches `xyz789` -- file on disk contains the new value

## Shortest path

**1 tool call**: a single `bash` call with `sed` to replace `abc123` with `xyz789`. The `bash` tool has no prerequisites. `max_tool_count` allows up to 2.

## Fail modes

- Uses 3+ tool calls (read + edit + verify, or grep + edit + read) -- excessive steps
- Calls `edit` without reading first -- tool will error at runtime due to `filetime.assert`
- Uses `grep` to find the old value before replacing -- the prompt already provides it
- Replacement fails on disk (wrong `oldString`, wrong file path, etc.)
