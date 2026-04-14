# #33 write

## Category

tool_schema

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `write` tool. Opencode uses `write` (not `create` or `create_file`) with `filePath` and `content` parameters. This test verifies the model uses the correct tool and parameter names for file creation, and that the written content matches exactly.

## Setup

The file `src/id.txt` does not exist in the fixture. The prompt asks to create it from scratch.

## Prompt

> Create a new file src/id.txt containing exactly: BENCH_7d4e

## Pass criteria (7 checks)

1. `any_tool_name` equals `write` -- model calls the `write` tool
2. `no_tool_name` not equals `bash` -- does not use bash echo/redirect instead
3. `no_tool_name` not equals `edit` -- does not use edit for new file creation
4. `any_tool_param_exists` `write.filePath` -- uses the correct file path parameter
5. `any_tool_param_exists` `write.content` -- uses the correct content parameter
6. `any_tool_param_regex` `write.content` matches `^BENCH_7d4e\s*$` -- content is exactly `BENCH_7d4e`
7. `file_regex` `src/id.txt` matches `^BENCH_7d4e\s*$` -- file contains exactly `BENCH_7d4e`

## Shortest path

**1 tool call**: `write` with `filePath` and `content`. The file doesn't exist, so `filetime.assert` is skipped. No tool call checks constrain the upper bound.

## Fail modes

- Uses `bash echo >` instead of the native `write` tool
- Uses `edit` tool (meant for modifying existing files, not creating new ones)
- Hallucinated tool name like `create_file` or `touch`
- Writes the marker with extra content (e.g., explanatory comments or newlines) -- fails anchored exact check
- Calls write with correct params but the file is not created on disk
