# #14 bash_search

## Category

prompt_tool_restriction

## Project

bash_only

## Capability

Prompt-based tool restriction -- content search via bash only. Similar to #13, but the task requires searching for a string across files. The model must use `bash grep` or `bash rg` instead of the native `grep` or `read` tools.

## Setup

Same `bash_only` project. The file `src/app.ts` contains the string `NEEDLE_abc1` as a comment.

## Prompt (run with `--agent bash_only`)

> Which file in src/ contains the string NEEDLE_abc1?

## Pass criteria (5 checks)

1. `any_tool_name` equals `bash` -- model uses bash
2. `no_tool_name` not `grep` -- does not use the native grep tool
3. `no_tool_name` not `read` -- does not use the native read tool
4. `any_tool_param_regex` `bash.command` matches `NEEDLE_abc1` -- bash command searches for the actual needle string
5. `text_contains` `app\.ts` -- response identifies the correct file

## Shortest path

**1 tool call**: a single `bash` call (e.g. `grep -r NEEDLE_abc1 src/`). The `bash` tool has no prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses the native `grep` tool -- ignores the bash-only restriction
- Uses `read` to manually inspect files one by one
- Runs a bash command that doesn't actually search for `NEEDLE_abc1` (e.g., hardcodes the answer)
- Identifies the wrong file
