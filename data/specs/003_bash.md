# #3 bash

**Category:** tool_schema
**Project:** default

## Capability

Tool schema adherence for the `bash` tool. Opencode's bash tool requires both a `command` parameter (the shell command to run) and a `description` parameter (a short human-readable summary of what the command does). This test verifies the model provides both required parameters.

## Setup

No special project files needed. The prompt asks for a simple echo command.

## Prompt

> Run the command: echo BENCH_OK

## Pass criteria

- Model calls the `bash` tool
- Provides both `description` and `command` parameters
- Output text contains `BENCH_OK`

## Fail modes

- Omits the `description` parameter (which is required by opencode's bash tool schema)
- Doesn't call bash at all and just responds with text
