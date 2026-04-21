# #7 create_file

## Category

efficiency

## Contract

completion

## Surface

tools

## Capability

Tool call efficiency -- direct file creation without exploration. When asked to create a new file with specified content, the model should call `write` once. There is no need to glob to "check the directory," read existing files to "match style," or use bash to verify the path. This tests whether the model can act directly on a creation request.

## Design rationale

Many models have a learned pattern of exploring the project structure before writing new files -- globbing for existing files in the directory, reading adjacent files to match conventions, or checking if the file already exists. When the prompt explicitly says "the file doesn't exist yet" and provides exact content, any exploration is pure waste.

This differs from #8 (`direct_edit`) which tests edit efficiency. Here, the model uses the `write` tool (for creation) rather than `edit` (for modification). It also differs from #33 (`write` in tool_schema) which tests correct parameter names without efficiency constraints.

## Setup

The file `src/config.ts` does not exist. The prompt asks to create it with specific content.

## Prompt

> Create a new file src/config.ts containing exactly: `export const DEBUG = true`. The file doesn't exist yet -- just create it.

## Pass criteria (7 checks)

1. `any_tool_name` equals `write` -- uses the write tool
2. `max_tool_count` max 1 -- exactly one tool call
3. `no_tool_name` not `read` -- does not read any files
4. `no_tool_name` not `glob` -- does not glob the directory
5. `tool_count_score` optimal 1, limit 1 -- optimal and maximum is 1 tool call
6. `file_regex` `src/config.ts` matches `^export const DEBUG = true\s*$` -- file contains exactly `export const DEBUG = true`
7. `call_schema_valid` -- all tool calls validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `write` to create `src/config.ts`. The file doesn't exist in the fixture, so `filetime.assert` is skipped. `max_tool_count` is set to 1.

## Fail modes

- Globs `src/` to check directory contents before writing -- unnecessary exploration
- Reads `src/utils.ts` or `src/index.ts` to "match the project style" -- not requested
- Uses `bash mkdir -p` before writing -- the write tool handles directory creation
- Uses `edit` instead of `write` for a new file -- wrong tool selection
