# #26 edit

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `edit` tool. Opencode's edit tool uses camelCase parameters (`filePath`, `oldString`, `newString`). This test verifies the model selects `edit` (not `bash sed`), sequences it correctly after `read`, and produces the intended file outcome. Parameter-name correctness (including rejection of snake_case variants like `old_string`) is enforced universally by `call_schema_valid`.

## Setup

The project contains `src/utils.ts` with a TOKEN constant set to a UUID value.

## Prompt

> In src/utils.ts, change the TOKEN value from the current UUID to a new UUID.

## Pass criteria (4 checks)

1. `any_tool_name_recursive` equals `edit` -- edit happens at some layer (parent or subagent)
2. `tool_before` read → edit -- deliberately strict at the parent layer: the filetime.assert guard only applies to the main agent's own read/edit ordering
3. `file_regex` `src/utils.ts` -- file on disk contains the new token value
4. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**2 tool calls**: `read` src/utils.ts, then `edit`. The edit tool's `filetime.assert` enforces the read at runtime. No tool call checks constrain the upper bound.

## Fail modes

- Uses `bash sed` instead of the native `edit` tool
- Provides incorrect replacement value (file on disk ends up with the wrong UUID)
- Calls edit with correct params but the edit fails to apply (e.g., oldString doesn't match file content)
- Emits snake_case (`old_string`) or other unknown params -- caught universally by `call_schema_valid`
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
