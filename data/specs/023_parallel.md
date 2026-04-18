# #23 parallel

## Category

tool_orchestration

## Contract

completion

## Surface

tools

## Capability

Parallel tool execution -- the model should issue multiple independent tool calls within a single step when explicitly asked. Opencode supports parallel tool use (multiple tool calls in the same assistant turn). This test verifies the model can read two files simultaneously rather than sequentially.

## Setup

The project contains `src/index.ts` with a MARKER UUID and `src/auth.ts` with a different MARKER UUID.

## Prompt

> Read both src/index.ts and src/auth.ts at the same time and tell me both marker values.

## Pass criteria (4 checks)

1. `min_tool_count` `read` >= 2 -- at least two read calls in the trace
2. `tools_same_step` `read` >= 2 -- both reads occur in the same assistant turn
3. `text_contains_from_file` -- response includes the MARKER value from `src/index.ts` (derived at eval time)
4. `text_contains_from_file` -- response includes the MARKER value from `src/auth.ts` (derived at eval time)

## Shortest path

**2 tool calls**: two parallel `read` calls. The `tools_same_step` check requires both in the same turn. No tool call checks constrain the upper bound.

## Fail modes

- Reads files sequentially in separate steps (ignores "at the same time")
- Reads only one file
- Reports markers incorrectly or omits one
