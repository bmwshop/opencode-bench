# #16 creates_plan_file

## Category

plan_mode

## Project

plan_default

## Capability

Plan mode file creation. In plan mode, the model should write plans to `.opencode/plans/*.md` using the `edit` tool (not `write`). This tests whether the model understands the plan mode convention: it can create/edit markdown plan files in the designated directory, and uses `edit` (the only write-capable tool allowed) rather than `write`.

## Setup

The `plan_default` project permits `edit` only for paths matching `.opencode/plans/*.md`. The `write` tool has no explicit allow, so it defaults to denied.

## Prompt (run with `--agent plan`)

> Create a detailed plan for refactoring src/auth.ts to use JWT-based authentication.

## Pass criteria (4 checks)

1. `any_tool_name` equals `edit` -- model uses the edit tool
2. `any_tool_param_regex` `edit.filePath` matches `plans/.*\.md` -- targets a plan file path
3. `no_tool_name` not `write` -- does not use the write tool
4. `file_exists` `.opencode/plans` -- the plans directory was actually created on disk

## Fail modes

- Uses `write` instead of `edit` (write is not permitted in this project's plan mode config)
- Creates the plan file outside of `.opencode/plans/` directory
- Outputs the plan only as response text without persisting it to a file
