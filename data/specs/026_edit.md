# #26 edit

## Category

tool_schema

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `edit` tool. Opencode's edit tool uses camelCase parameters (`filePath`, `oldString`, `newString`). Models may hallucinate snake_case variants (`old_string`, `new_string`) from other frameworks. This test verifies correct parameter naming and that the edit payload contains the intended replacement value.

## Setup

The project contains `src/utils.ts` with a TOKEN constant set to a UUID value.

## Prompt

> In src/utils.ts, change the TOKEN value from the current UUID to a new UUID.

## Pass criteria (9 checks)

1. `any_tool_name` equals `edit` -- model calls the `edit` tool
2. `any_tool_param_exists` `edit.filePath` -- uses correct file path parameter
3. `any_tool_param_exists` `edit.oldString` -- uses correct old string parameter
4. `any_tool_param_exists` `edit.newString` -- uses correct new string parameter
5. `any_tool_param_absent` `edit.old_string` -- does not use snake_case variant
6. `any_tool_param_absent` `edit.new_string` -- does not use snake_case variant
7. `any_tool_param_regex` `edit.newString` -- replacement value matches the new UUID from the prompt
8. `tool_before` read → edit -- read before edit (filetime.assert enforced)
9. `file_regex` `src/utils.ts` -- file on disk contains the new token value

## Shortest path

**2 tool calls**: `read` src/utils.ts, then `edit`. The edit tool's `filetime.assert` enforces the read at runtime. No tool call checks constrain the upper bound.

## Fail modes

- Uses snake_case parameter names (`old_string`, `new_string`) from other agent conventions
- Uses `bash sed` instead of the native `edit` tool
- Provides incorrect replacement value
- Calls edit with correct params but the edit fails to apply (e.g., oldString doesn't match file content)
