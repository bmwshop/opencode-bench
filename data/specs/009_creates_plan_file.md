# #9 creates_plan_file

## Category

plan_mode

## Project

plan_default

## Contract

completion

## Surface

modes

## Capability

Plan mode file creation. When plan mode is active and no plan file exists yet, the opencode plan mode prompt instructs the model to create the plan using the `write` tool at the path `.opencode/plans/<timestamp>-<slug>.md`. This tests whether the model follows that instruction and writes to the correct directory.

## Setup

The `plan_default` project permits both `write` and `edit` for paths matching `.opencode/plans/*.md`. Other write-capable operations are denied. The plan mode system prompt (injected by opencode at runtime) tells the model: "No plan file exists yet. You should create your plan at {path} using the write tool."

## Prompt (run with `--agent plan`)

> Create a detailed plan for refactoring src/auth.ts to use JWT-based authentication.

## Pass criteria (5 checks)

1. `any_tool_name` equals `write` -- model uses the write tool (as instructed by plan mode prompt)
2. `any_tool_param_regex` `write.filePath` matches `plans/.*\.md` -- targets a plan file path
3. `no_tool_name` not `edit` -- does not use edit (plan mode prompt says to use write for new plans)
4. `file_exists` `.opencode/plans` -- the plans directory was actually created on disk
5. `any_tool_param_regex` `write.content` matches `(?i)jwt|token|auth` -- plan content is substantive (mentions JWT, token, or auth)

## Shortest path

**1 tool call**: `write` to create the plan file under `.opencode/plans/`. The file doesn't exist, so `filetime.assert` is skipped. No prior read needed.

## Fail modes

- Uses `edit` instead of `write` -- plan mode prompt explicitly says "using the write tool" for new plans
- Creates the plan file outside of `.opencode/plans/` directory
- Outputs the plan only as response text without persisting it to a file
- Writes an empty or placeholder file with no meaningful plan content
