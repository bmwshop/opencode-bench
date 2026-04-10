# #4 write

## Category

tool_schema

## Project

default

## Capability

Tool schema adherence for the `write` tool. Opencode uses `write` (not `create` or `create_file`) with `filePath` and `content` parameters. This test verifies the model uses the correct tool and parameter names for file creation, and that the written content matches exactly.

## Setup

No special project files needed. The prompt asks to create a new file.

## Prompt

> Create a new file src/id.txt containing exactly: BENCH_7d4e

## Pass criteria (4 checks)

1. `any_tool_name` equals `write` -- model calls the `write` tool
2. `any_tool_param_exists` `write.filePath` -- uses the correct file path parameter
3. `any_tool_param_exists` `write.content` -- uses the correct content parameter
4. `any_tool_param_regex` `write.content` matches `BENCH_7d4e` -- content contains the marker

## Fail modes

- Uses `bash echo >` instead of the native `write` tool
- Uses `edit` tool (meant for modifying existing files, not creating new ones)
- Hallucinated tool name like `create_file` or `touch`
