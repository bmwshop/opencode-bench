# #20 bash_pipe

- **Category:** prompt_tool_restriction
- **Project:** bash_only

## Capability

Prompt-based tool restriction -- shell pipes. This extends the bash-only restriction to a task that naturally calls for `glob` (counting files by pattern). The model must accomplish this using bash with a pipe (e.g., `ls src/*.ts | wc -l` or `find src -name '*.ts' | wc -l`), testing both tool restriction adherence and shell proficiency.

## Setup

Same `bash_only` project. The `src/` directory contains exactly 3 `.ts` files: `app.ts`, `config.ts`, `main.ts`.

## Prompt (run with `--agent bash_only`)

> Count how many .ts files exist in src/ and report the exact number.

## Pass criteria

- Model calls the `bash` tool
- Does NOT call `glob`
- The bash `command` contains a pipe character (`|`)
- Response text includes the number `3`

## Fail modes

- Uses the native `glob` tool -- ignores the bash-only restriction
- Uses bash but without a pipe (e.g., just `ls src/*.ts` and counts visually)
- Reports the wrong count
