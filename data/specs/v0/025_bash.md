# #25 bash

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `bash` tool. Opencode's bash tool requires both a `command` parameter (the shell command to run) and a `description` parameter (a short human-readable summary of what the command does). This test verifies the model provides both required parameters.

## Setup

No special project files needed. The prompt asks for a simple echo command.

## Prompt

> Run the command: echo \<UUID\>

## Pass criteria (3 checks)

1. `any_tool_name_recursive` equals `bash` -- bash happens at some layer (parent or subagent)
2. `text_contains` -- output includes the echoed UUID from the prompt
3. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `bash` with `command` and `description`. No tool call checks constrain the upper bound.

## Fail modes

- Omits the `description` parameter (which is required by opencode's bash tool schema)
- Doesn't call bash at all and just responds with text
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
