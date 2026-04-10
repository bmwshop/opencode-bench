# #19 bash_search

## Category

prompt_tool_restriction

## Project

bash_only

## Capability

Prompt-based tool restriction -- content search via bash only. Similar to #18, but the task requires searching for a string across files. The model must use `bash grep` or `bash rg` instead of the native `grep` or `read` tools.

## Setup

Same `bash_only` project. The file `src/app.ts` contains the string `NEEDLE_abc1` as a comment.

## Prompt (run with `--agent bash_only`)

> Which file in src/ contains the string NEEDLE_abc1?

## Pass criteria (4 checks)

1. `any_tool_name` equals `bash` -- model uses bash
2. `no_tool_name` not `grep` -- does not use the native grep tool
3. `no_tool_name` not `read` -- does not use the native read tool
4. `text_contains` `app\.ts` -- response identifies the correct file

## Fail modes

- Uses the native `grep` tool -- ignores the bash-only restriction
- Uses `read` to manually inspect files one by one
- Identifies the wrong file
