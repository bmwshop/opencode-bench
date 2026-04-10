# #5 glob

**Category:** tool_schema  
**Project:** default

## Capability

Tool selection -- choosing the `glob` tool for file-pattern discovery. When asked to find files matching a pattern, the model should use opencode's native `glob` tool rather than falling back to `bash` with `find` or `ls`. This tests whether the model understands which opencode tool fits the task.

## Setup

The project contains test files (`src/auth.test.ts`, `src/utils.test.ts`) that match a test file pattern.

## Prompt

> Find all test files in this project.

## Pass criteria

- Model calls the `glob` tool
- Does not use `bash` (e.g., `find`, `ls`)

## Fail modes

- Uses `bash find` or `bash ls` instead of the native `glob` tool
- Uses `grep` to search for test patterns in file contents instead of discovering files by name
