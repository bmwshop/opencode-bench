# #31 read

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `read` tool. Opencode exposes a `read` tool with the parameter `filePath` (camelCase). This test verifies the model uses the native `read` tool (not `bash cat`), reads the requested file, and reports the marker. Rejection of hallucinated param names like `path` is enforced universally by `call_schema_valid`.

## Setup

The project contains `src/index.ts` with a MARKER UUID on the first line.

## Prompt

> Read the file src/index.ts and tell me the marker value.

## Pass criteria (3 checks)

1. `any_tool_name_recursive` equals `read` -- read happens at some layer (parent or subagent)
2. `text_contains_from_file` -- response mentions the MARKER value from `src/index.ts` (derived at eval time)
3. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `read` with `filePath` set to `src/index.ts`. No prerequisites.

## Fail modes

- Uses `bash` with `cat` instead of the native `read` tool
- Reads the file but doesn't report the marker value in response text
- Emits hallucinated param names like `path` -- caught universally by `call_schema_valid`
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
