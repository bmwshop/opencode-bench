# #33 write

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `write` tool. Opencode uses `write` (not `create` or `create_file`) with `filePath` and `content` parameters. This test verifies the model uses the correct tool and parameter names for file creation, and that the written content matches exactly.

## Setup

The file `src/id.txt` does not exist in the fixture. The prompt asks to create it from scratch.

## Prompt

> Create a new file src/id.txt containing exactly: \<UUID\>

## Pass criteria (3 checks)

1. `any_tool_name_recursive` equals `write` -- write happens at some layer (parent or subagent)
2. `file_regex` `src/id.txt` -- file on disk contains exactly the UUID from the prompt
3. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `write` with `filePath` and `content`. The file doesn't exist, so `filetime.assert` is skipped.

## Fail modes

- Uses `bash echo >` instead of the native `write` tool
- Uses `edit` tool (meant for modifying existing files, not creating new ones)
- Hallucinated tool name like `create_file` or `touch` -- rejected by `call_schema_valid`
- Writes the UUID with extra content (e.g., explanatory comments or newlines) -- fails the anchored file check
- Calls write with correct params but the file is not created on disk
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
