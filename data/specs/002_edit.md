# #2 edit

## Category

tool_schema

## Project

default

## Capability

Tool schema adherence for the `edit` tool. Opencode's edit tool uses camelCase parameters (`filePath`, `oldString`, `newString`). Models may hallucinate snake_case variants (`old_string`, `new_string`) from other frameworks. This test verifies correct parameter naming and that the edit payload contains the intended replacement value.

## Setup

The project contains `src/utils.ts` with `export const TOKEN = "abc123"`.

## Prompt

> In src/utils.ts, change the TOKEN value from "abc123" to "xyz789".

## Pass criteria

- Model calls the `edit` tool
- Uses `filePath`, `oldString`, `newString` parameters
- Does not use `old_string` or `new_string`
- `newString` value contains `xyz789`

## Fail modes

- Uses snake_case parameter names (`old_string`, `new_string`) from other agent conventions
- Uses `bash sed` instead of the native `edit` tool
- Provides incorrect replacement value
