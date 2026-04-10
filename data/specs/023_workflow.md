# #23 workflow

**Category:** skill  
**Project:** skill_workflow

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

## Pass criteria

- Model calls the `skill` tool (loads the review-flow skill)
- `read` tool is called before `bash` (follows the prescribed step order)
- An output file `review.md` is created with a `# Review` heading

## Fail modes

- Doesn't load the skill -- reviews the file using its own judgment without the workflow
- Loads the skill but doesn't follow the step order (e.g., runs grep before reading)
- Doesn't create the `review.md` output file
- Creates the output file but with wrong format (missing `# Review` heading)
