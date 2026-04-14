# #17 workflow

## Category

skill

## Project

skill_workflow

## Capability

Workflow-based skill execution. Some skills define multi-step procedures rather than just conventions. This test verifies the model loads a workflow skill and follows its prescribed sequence of steps: (1) read the target file, (2) run a bash command to count TODOs, (3) write findings to a specific output file with a required format.

## Setup

The project has a skill named `review-flow` at `.opencode/skills/review-flow/SKILL.md` that defines a code review workflow:
1. Read the target file
2. Run: `grep -c "TODO" <file>` to count TODOs
3. Write findings to `review.md` with heading `# Review: <filename>`

The file `src/app.ts` contains 2 TODO comments.

## Prompt

> Review src/app.ts

## Pass criteria (4 checks)

1. `any_tool_name` equals `skill` -- model invokes the skill tool
2. `any_tool_param_value` `skill.name` equals `review-flow` -- loads the correct skill
3. `tool_before` `read` then `bash` -- reads the file before running the grep command
4. `file_regex` `review.md` matches `# Review` -- output file has the required heading

## Shortest path

**3 tool calls**: `skill` (with `name: "review-flow"`), `read` src/app.ts, then `bash` (grep for TODOs). The `tool_before` check requires both `read` and `bash` with read first. The fixture already has `review.md` with the correct heading, so the `file_regex` check passes without the model writing it.

## Fail modes

- Doesn't load the skill -- reviews the file using its own judgment without the workflow
- Loads the skill but doesn't follow the step order (e.g., runs grep before reading)
- Doesn't create the `review.md` output file
- Creates the output file but with wrong format (missing `# Review` heading)
