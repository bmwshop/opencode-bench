# #3 focused_read

## Category

distractor

## Contract

completion

## Surface

tools

## Capability

Distractor resistance -- precision under noise. The prompt mentions multiple source files and test files, but the task only requires reading one. The model must resist the temptation to read extra files, grep for markers, or delegate to a subagent. This tests whether the model can extract the precise action from a noisy prompt.

## Design rationale

The project has markers in multiple files: `src/index.ts` and `src/auth.ts` each contain a unique MARKER UUID. The prompt names both files (and more), creating a realistic temptation. A model that reads `auth.ts` in addition to `index.ts` wastes a tool call and might even report the wrong marker. The phrase "nothing else" is an explicit constraint that the model must respect.

## Setup

The relevant files:
- `src/index.ts` -- contains a MARKER UUID (the target)
- `src/auth.ts` -- contains a different MARKER UUID (the distractor)
- `src/utils.ts`, `src/auth.test.ts`, `src/utils.test.ts` -- additional distractors

## Prompt

> This project has src/auth.ts, src/utils.ts, src/index.ts, and their test files. I only need the marker value from index.ts -- nothing else.

## Pass criteria (5 checks)

1. `any_tool_name_recursive` equals `read` -- read happens at some layer (parent or subagent)
2. `text_contains_from_file` -- reports the correct MARKER value from `src/index.ts` (derived at eval time)
3. `no_tool_name_recursive` not `grep` -- no grep at any layer (outcome-focused)
4. `no_tool_name` not `task` -- deliberately strict: the parent must not delegate on this trivial lookup
5. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: read `src/index.ts`, then report the marker. The `read` tool has no prerequisites.

## Fail modes

- Reads all source files -- ignores "nothing else" and over-explores
- Reads `src/auth.ts` and reports the wrong marker -- reads the wrong file or reports the distractor marker
- Greps for "marker" across the project -- unnecessary search when the file is specified
- Delegates to a subagent -- over-engineering a simple read task (caught by the strict `no_tool_name: task`)
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
