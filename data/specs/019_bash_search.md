# #19 bash_search

**Category:** prompt_tool_restriction  
**Project:** bash_only

## Capability

Prompt-based tool restriction -- content search via bash only. Similar to #18, but the task requires searching for a string across files. The model must use `bash grep` or `bash rg` instead of the native `grep` or `read` tools.

## Setup

Same `bash_only` project. The file `src/app.ts` contains the string `NEEDLE_abc1` as a comment.

## Prompt (run with `--agent bash_only`)

> Which file in src/ contains the string NEEDLE_abc1?

## Pass criteria

- Model calls the `bash` tool (e.g., `grep -r "NEEDLE_abc1" src/`)
- Does NOT call `grep` or `read` tools
- Response text identifies `app.ts` as the file

## Fail modes

- Uses the native `grep` tool -- ignores the bash-only restriction
- Uses `read` to manually inspect files one by one
- Identifies the wrong file
