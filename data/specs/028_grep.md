# #28 grep

## Category

tool_schema

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool selection -- choosing the `grep` tool for content search. When asked to find a string inside files, the model should use opencode's native `grep` tool rather than `bash grep` or reading files one by one. This also tests that the model correctly identifies the file containing the needle.

## Setup

The project contains `src/auth.ts` with the string `NEEDLE_f9c2` embedded as a comment.

## Prompt

> Find which file contains the string NEEDLE_f9c2.

## Pass criteria (3 checks)

1. `any_tool_name` equals `grep` -- model calls the `grep` tool
2. `no_tool_name` not `bash` -- does not fall back to shell commands
3. `text_contains` `auth\.ts` -- response identifies the correct file

## Shortest path

**1 tool call**: `grep` with pattern `NEEDLE_f9c2`. No prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses `bash grep` or `bash rg` instead of the native `grep` tool
- Reads files one by one with `read` looking for the string manually
- Identifies the wrong file
