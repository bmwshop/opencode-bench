# #8 parallel

**Category:** tool_orchestration
**Project:** default

## Capability

Parallel tool execution -- the model should issue multiple independent tool calls within a single step when explicitly asked. Opencode supports parallel tool use (multiple tool calls in the same assistant turn). This test verifies the model can read two files simultaneously rather than sequentially.

## Setup

The project contains `src/index.ts` with marker `8f3a2b1c` and `src/auth.ts` with marker `b7e1d930`.

## Prompt

> Read both src/index.ts and src/auth.ts at the same time and tell me both marker values.

## Pass criteria

- At least 2 `read` tool calls in the trace
- Both `read` calls occur in the same step (same assistant turn)
- Response text includes both markers: `8f3a2b1c` and `b7e1d930`

## Fail modes

- Reads files sequentially in separate steps (ignores "at the same time")
- Reads only one file
- Reports markers incorrectly or omits one
