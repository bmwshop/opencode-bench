# #23 parallel

## Category

tool_orchestration

## Project

default

## Capability

Parallel tool execution -- the model should issue multiple independent tool calls within a single step when explicitly asked. Opencode supports parallel tool use (multiple tool calls in the same assistant turn). This test verifies the model can read two files simultaneously rather than sequentially.

## Setup

The project contains `src/index.ts` with marker `8f3a2b1c` and `src/auth.ts` with marker `b7e1d930`.

## Prompt

> Read both src/index.ts and src/auth.ts at the same time and tell me both marker values.

## Pass criteria (4 checks)

1. `min_tool_count` `read` >= 2 -- at least two read calls in the trace
2. `tools_same_step` `read` >= 2 -- both reads occur in the same assistant turn
3. `text_contains` `8f3a2b1c` -- response includes the index.ts marker
4. `text_contains` `b7e1d930` -- response includes the auth.ts marker

## Shortest path

**2 tool calls in 1 model turn**: two parallel `read` calls. The `tools_same_step` check requires both in the same turn. No tool call checks constrain the upper bound.

## Fail modes

- Reads files sequentially in separate steps (ignores "at the same time")
- Reads only one file
- Reports markers incorrectly or omits one
