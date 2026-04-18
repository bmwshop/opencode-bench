# #24 sequential

## Category

tool_orchestration

## Project

default

## Contract

completion

## Surface

tools

## Capability

Sequential tool execution -- the model must chain tools in the correct order when the task has a natural dependency. Reading a file before editing it is a common pattern in coding agents. This test verifies the model calls `read` before `edit`, not the other way around or in parallel.

## Setup

The project contains `src/utils.ts` with a TOKEN constant set to a UUID value.

## Prompt

> Read src/utils.ts, then change the TOKEN value from the current UUID to a new UUID.

## Pass criteria (3 checks)

1. `tool_before` `read` then `edit` -- read is called before edit in the trace
2. `any_tool_param_regex` `edit.newString` -- replacement value matches the new UUID from the prompt
3. `file_regex` `src/utils.ts` -- file on disk contains the new token value

## Shortest path

**2 tool calls**: `read` src/utils.ts, then `edit`. The edit tool's `filetime.assert` also enforces this ordering at runtime. No tool call checks constrain the upper bound.

## Fail modes

- Calls `edit` without reading first (skips the explicit "read first" instruction)
- Calls both in the same step / parallel (ignores the sequential "then" in the prompt)
- Edits with the wrong replacement value
- Edit call succeeds in the trace but the file is not actually modified on disk
