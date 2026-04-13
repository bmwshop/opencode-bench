# #31 read

## Category

tool_schema

## Project

default

## Capability

Tool schema adherence for the `read` tool. Opencode exposes a `read` tool with the parameter `filePath` (camelCase). Models trained on other coding agents may hallucinate a `path` parameter instead. This test verifies the model uses the correct opencode-native parameter name and successfully retrieves file content.

## Setup

The project contains `src/index.ts` with a known marker value `8f3a2b1c` on the first line.

## Prompt

> Read the file src/index.ts and tell me the marker value.

## Pass criteria (4 checks)

1. `any_tool_name` equals `read` -- model calls the `read` tool
2. `any_tool_param_exists` `read.filePath` -- uses the correct parameter name
3. `any_tool_param_absent` `read.path` -- does not use the wrong parameter name
4. `text_contains` `8f3a2b1c` -- response mentions the marker value

## Fail modes

- Uses `bash` with `cat` instead of the native `read` tool
- Calls `read` with wrong parameter name `path` (common hallucination from other agent frameworks)
- Reads the file but doesn't report the marker value in response text
