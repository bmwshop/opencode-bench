# #28 grep

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool selection -- choosing the `grep` tool for content search. When asked to find a string inside files, the model should use opencode's native `grep` tool rather than `bash grep` or reading files one by one. This also tests that the model correctly identifies the file containing the needle.

## Setup

The project contains `src/auth.ts` with a NEEDLE comment containing a UUID suffix.

## Prompt

> Find which file contains the NEEDLE string. (The exact NEEDLE value is provided in the prompt.)

## Pass criteria (3 checks)

1. `any_tool_name_recursive` equals `grep` -- grep happens at some layer (parent or subagent)
2. `text_contains` `auth\.ts` -- response identifies the correct file
3. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `grep` with the NEEDLE pattern. No prerequisites.

## Fail modes

- Uses `bash grep` or `bash rg` instead of the native `grep` tool
- Reads files one by one with `read` looking for the string manually
- Identifies the wrong file
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
