# #31 read

## Category

tool_schema

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `read` tool. Opencode exposes a `read` tool with the parameter `filePath` (camelCase). Models trained on other coding agents may hallucinate a `path` parameter instead. This test verifies the model uses the correct opencode-native parameter name and successfully retrieves file content.

## Setup

The project contains `src/index.ts` with a MARKER UUID on the first line.

## Prompt

> Read the file src/index.ts and tell me the marker value.

## Pass criteria (5 checks)

1. `any_tool_name` equals `read` -- model calls the `read` tool
2. `max_tool_count` max 1 -- exactly one tool call
3. `any_tool_param_exists` `read.filePath` -- uses the correct parameter name
4. `any_tool_param_absent` `read.path` -- does not use the wrong parameter name
5. `text_contains_from_file` -- response mentions the MARKER value from `src/index.ts` (derived at eval time)

## Shortest path

**1 tool call**: `read` with `filePath` set to `src/index.ts`. No prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses `bash` with `cat` instead of the native `read` tool
- Calls `read` with wrong parameter name `path` (common hallucination from other agent frameworks)
- Reads the file but doesn't report the marker value in response text
