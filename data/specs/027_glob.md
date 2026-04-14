# #27 glob

## Category

tool_schema

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool selection -- choosing the `glob` tool for file-pattern discovery. When asked to find files matching a pattern, the model should use opencode's native `glob` tool rather than falling back to `bash` with `find` or `ls`. This tests whether the model understands which opencode tool fits the task.

## Setup

The project contains test files (`src/auth.test.ts`, `src/utils.test.ts`) that match a test file pattern.

## Prompt

> Find all test files in this project.

## Pass criteria (5 checks)

1. `any_tool_name` equals `glob` -- model calls the `glob` tool
2. `no_tool_name` not `bash` -- does not fall back to shell commands
3. `any_tool_param_regex` `glob.pattern` matches `test|spec` -- glob pattern targets test files
4. `text_contains` `auth\.test\.ts` -- response mentions auth.test.ts
5. `text_contains` `utils\.test\.ts` -- response mentions utils.test.ts

## Shortest path

**1 tool call**: `glob` with a pattern like `**/*.test.ts`. No prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses `bash find` or `bash ls` instead of the native `glob` tool
- Uses `grep` to search for test patterns in file contents instead of discovering files by name
- Calls `glob` with a pattern that doesn't target test files (e.g., `**/*.ts` instead of `**/*.test.ts`)
- Returns the glob results without listing the actual filenames in the response
