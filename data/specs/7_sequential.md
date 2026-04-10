# #7 sequential

**Category:** tool_orchestration
**Project:** default

## Capability

Sequential tool execution -- the model must chain tools in the correct order when the task has a natural dependency. Reading a file before editing it is a common pattern in coding agents. This test verifies the model calls `read` before `edit`, not the other way around or in parallel.

## Setup

The project contains `src/utils.ts` with `export const TOKEN = "abc123"`.

## Prompt

> Read src/utils.ts, then change the TOKEN value from "abc123" to "xyz789".

## Pass criteria

- Model calls `read` before `edit` (by tool call index in the trace)
- The `edit` call's `newString` contains `xyz789`

## Fail modes

- Calls `edit` without reading first (skips the explicit "read first" instruction)
- Calls both in the same step / parallel (ignores the sequential "then" in the prompt)
- Edits with the wrong replacement value
