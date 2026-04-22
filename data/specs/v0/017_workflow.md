# #17 workflow

## Category

skill

## Contract

completion

## Surface

skills

## Capability

Workflow-based skill execution. Some skills define multi-step procedures rather than just conventions. This test verifies the model loads a workflow skill and produces the correct output file with the required format. The specific tool choices (bash vs read, write vs edit) are not constrained -- only the outcome matters.

## Setup

The project has a skill named `review-flow` at `.opencode/skills/review-flow/SKILL.md` that defines a code review workflow:
1. Read the target file
2. Run: `grep -c "TODO" <file>` to count TODOs
3. Write findings to `review.md` with heading `# Review: <filename>`

The file `src/app.ts` contains 2 TODO comments.

## Prompt

> Review src/app.ts

## Pass criteria (6 checks)

1. `any_tool_name_recursive` equals `skill` -- skill is invoked at some layer (parent or subagent)
2. `any_tool_param_value_recursive` `skill.name` equals `review-flow` -- the correct skill is loaded, at any layer
3. `file_regex` `review.md` matches `# Review` -- output file has the required heading
4. `file_regex` `review.md` matches `app\.ts` -- review mentions the target filename
5. `file_regex` `review.md` matches `TODO Count.*2` -- review includes the correct TODO count
6. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

Note: previous checks requiring `tool_before read -> bash` and `any_tool_name write` were removed. Models may count TODOs via `read` instead of `bash grep`, and may use `edit` instead of `write` to create `review.md`. The outcome checks (3-5) validate correctness regardless of tool choice.

## Shortest path

**4 tool calls**: `skill` (with `name: "review-flow"`) → `read src/app.ts` → `bash grep -c "TODO" src/app.ts` → `write review.md`. Alternative valid paths include counting TODOs via `read` and creating the file via `edit`.

## Fail modes

- Doesn't load the skill -- reviews the file using its own judgment without the workflow
- Doesn't create the `review.md` output file
- Creates the output file but with wrong format (missing `# Review` heading)
- Writes a generic review without the target filename in the heading
- Omits or miscounts the TODO count (fixture has exactly 2)
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
