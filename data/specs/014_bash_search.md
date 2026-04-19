# #14 bash_search

## Category

prompt_tool_restriction

## Contract

completion

## Surface

permissions

## Capability

AGENTS.md-based tool restriction -- content search via bash only. Similar to #13, but the task requires searching for a string across files. The model must use `bash grep` or `bash rg` instead of the native `grep` or `read` tools, following the `AGENTS.md` instruction over the system prompt's tool suggestions.

## Setup

Same project. The `AGENTS.md` instructs bash-only usage while all tools remain visible. The file `src/app.ts` contains a NEEDLE comment with a UUID suffix.

## Prompt

> Which file in src/ contains the NEEDLE string? (The exact NEEDLE value is provided in the prompt.)

## Pass criteria (6 checks)

1. `any_tool_name` equals `bash` -- model uses bash
2. `no_tool_name` not `grep` -- does not use the native grep tool
3. `no_tool_name` not `read` -- does not use the native read tool
4. `any_tool_param_regex` `bash.command` matches the NEEDLE string -- bash command searches for the actual needle value
5. `text_contains` `app\.ts` -- response identifies the correct file
6. `call_schema_valid` -- all tool calls validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: a single `bash` call (e.g. `grep -r NEEDLE_... src/`). The `bash` tool has no prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses the native `grep` tool -- ignores the bash-only restriction
- Uses `read` to manually inspect files one by one
- Runs a bash command that doesn't actually search for the needle string (e.g., hardcodes the answer)
- Identifies the wrong file
