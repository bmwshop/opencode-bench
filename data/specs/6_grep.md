# #6 grep

**Category:** tool_schema
**Project:** default

## Capability

Tool selection -- choosing the `grep` tool for content search. When asked to find a string inside files, the model should use opencode's native `grep` tool rather than `bash grep` or reading files one by one. This also tests that the model correctly identifies the file containing the needle.

## Setup

The project contains `src/auth.ts` with the string `NEEDLE_f9c2` embedded as a comment.

## Prompt

> Find which file contains the string NEEDLE_f9c2.

## Pass criteria

- Model calls the `grep` tool
- Does not use `bash` (e.g., `bash grep`, `bash rg`)
- Response text identifies `auth.ts` as the file containing the needle

## Fail modes

- Uses `bash grep` or `bash rg` instead of the native `grep` tool
- Reads files one by one with `read` looking for the string manually
- Identifies the wrong file
