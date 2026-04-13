# #8 direct_edit

## Category

efficiency

## Project

default

## Capability

Tool call efficiency -- editing directly when all information is provided. When the prompt gives the exact file path, old string, and new string, the model should call `edit` once without reading the file first. This tests whether the model avoids procedural waste (unnecessary `read` before `edit`) when the prompt already supplies everything needed.

## Design rationale

Many models have a learned pattern of "read first, then edit" regardless of whether reading is necessary. This is often correct (you need to see the file to know what to change), but when the prompt provides the exact old and new strings verbatim, reading first is pure waste -- it adds latency, cost, and an extra round trip. The prompt explicitly says "don't read the file first" to remove any ambiguity.

The `tool_count_score` check provides a graduated metric: 1 call is optimal, 2 is acceptable (model read first despite being told not to), 3+ fails. This allows distinguishing "slightly inefficient" from "wildly inefficient" in the output.

## Setup

Uses the default project. The file `src/utils.ts` contains `export const TOKEN = "abc123"`.

## Prompt

> In src/utils.ts, replace the line `export const TOKEN = "abc123"` with `export const TOKEN = "xyz789"`. You have all the info you need -- don't read the file first.

## Pass criteria (6 checks)

1. `any_tool_name` equals `edit` -- uses the edit tool
2. `any_tool_param_regex` `edit.newString` matches `xyz789` -- correct replacement value
3. `no_tool_name` not `read` -- does not read the file first
4. `max_tool_count` max 1 -- exactly one tool call
5. `tool_count_score` optimal 1, limit 2 -- 1 call is optimal, 2 acceptable, 3+ fails
6. `file_regex` `src/utils.ts` matches `xyz789` -- file on disk contains the new value

## Fail modes

- Calls `read` on `src/utils.ts` before editing -- procedural waste, ignores "don't read the file first"
- Calls `edit` correctly but also calls `read` after to verify -- unnecessary verification
- Calls `bash cat` to inspect the file first -- circumvents native tools and wastes a call
- Uses `grep` to find the old value before editing -- the prompt already provides it
