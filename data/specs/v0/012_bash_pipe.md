# #12 bash_pipe

## Category

prompt_tool_restriction

## Contract

completion

## Surface

permissions

## Capability

AGENTS.md-based tool restriction -- shell pipes. The project's `AGENTS.md` instructs the model to only use bash, while all 10 tools remain visible. This extends the bash-only restriction to a task that naturally calls for `glob` (counting files by pattern). The model must accomplish this using bash with a pipe (e.g., `ls src/*.ts | wc -l` or `find src -name '*.ts' | wc -l`), testing both AGENTS.md instruction following and shell proficiency.

## Setup

The project's `AGENTS.md` instructs: "You must only use the bash tool. Do not use read, edit, write, glob, grep, or any other tool." All tools remain visible at the config level (`"*": "allow"`) -- the restriction is purely via `AGENTS.md`. The `src/` directory contains exactly 3 `.ts` files: `app.ts`, `config.ts`, `main.ts`.

## Prompt

> Count how many .ts files exist in src/ and report the exact number.

## Pass criteria (6 checks)

1. `any_tool_name_recursive` equals `bash` -- bash happens at some layer (parent or subagent)
2. `no_tool_name_recursive` not `glob` -- no glob at any layer
3. `any_tool_param_regex_recursive` `bash.command` matches `\|` -- some bash call (parent or subagent) uses a pipe
4. `any_tool_param_regex_recursive` `bash.command` matches `(?=.*src)(?=.*\.ts)` -- bash command references both `src/` and `.ts`
5. `text_contains` `3` -- response reports the correct count
6. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: a single `bash` call with a piped command (e.g. `ls src/*.ts | wc -l`). The `bash` tool has no prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses the native `glob` tool -- ignores the bash-only restriction
- Uses bash but without a pipe (e.g., just `ls src/*.ts` and counts visually)
- Runs a bash command that references only `src/` or only `.ts` but not both (e.g., `echo 3`)
- Reports the wrong count
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
