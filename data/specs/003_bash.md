# #3 bash

## Category

tool_schema

## Project

default

## Capability

Tool schema adherence for the `bash` tool. Opencode's bash tool requires both a `command` parameter (the shell command to run) and a `description` parameter (a short human-readable summary of what the command does). This test verifies the model provides both required parameters.

## Setup

No special project files needed. The prompt asks for a simple echo command.

## Prompt

> Run the command: echo BENCH_OK

## Pass criteria (4 checks)

1. `any_tool_name` equals `bash` -- model calls the `bash` tool
2. `any_tool_param_exists` `bash.description` -- provides the required description parameter
3. `any_tool_param_exists` `bash.command` -- provides the required command parameter
4. `text_contains` `BENCH_OK` -- output includes the command result

## Fail modes

- Omits the `description` parameter (which is required by opencode's bash tool schema)
- Doesn't call bash at all and just responds with text
