# #12 bash_pipe

## Category

prompt_tool_restriction

## Project

bash_only

## Capability

Prompt-based tool restriction -- shell pipes. This extends the bash-only restriction to a task that naturally calls for `glob` (counting files by pattern). The model must accomplish this using bash with a pipe (e.g., `ls src/*.ts | wc -l` or `find src -name '*.ts' | wc -l`), testing both tool restriction adherence and shell proficiency.

## Setup

Same `bash_only` project. The `src/` directory contains exactly 3 `.ts` files: `app.ts`, `config.ts`, `main.ts`.

## Prompt (run with `--agent bash_only`)

> Count how many .ts files exist in src/ and report the exact number.

## Pass criteria (5 checks)

1. `any_tool_name` equals `bash` -- model uses bash
2. `no_tool_name` not `glob` -- does not use the native glob tool
3. `any_tool_param_regex` `bash.command` matches `\|` -- command contains a pipe
4. `any_tool_param_regex` `bash.command` matches `(?=.*src)(?=.*\.ts)` -- bash command references both `src/` and `.ts`
5. `text_contains` `3` -- response reports the correct count

## Shortest path

**1 tool call**: a single `bash` call with a piped command (e.g. `ls src/*.ts | wc -l`). The `bash` tool has no prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Uses the native `glob` tool -- ignores the bash-only restriction
- Uses bash but without a pipe (e.g., just `ls src/*.ts` and counts visually)
- Runs a bash command that references only `src/` or only `.ts` but not both (e.g., `echo 3`)
- Reports the wrong count
