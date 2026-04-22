# #4 verbose_context

## Category

distractor

## Contract

completion

## Surface

tools

## Capability

Distractor resistance -- architectural noise. The prompt front-loads a detailed paragraph describing the project's authentication module, utilities module, test files, and entry point before stating the actual task: read the version string from the entry point. The model must filter signal from noise and avoid reading files mentioned only as context.

## Design rationale

In real-world usage, users often dump project context before asking a simple question. An over-eager model interprets the context as an implicit request to explore those files. This sample tests whether the model can extract the one actionable item ("I just need the version string from the entry point") from a prompt that describes auth.ts, utils.ts, TOKEN, verify, and test files -- none of which are relevant.

This differs from #3 (`focused_read`) which lists files explicitly. Here, the distraction is *embedded in descriptive prose* rather than in a file listing, testing a different kind of filtering.

## Setup

The file `src/index.ts` contains a MARKER UUID comment and exports a version string (a UUID). The prompt describes `src/auth.ts` (verify function, token verification), `src/utils.ts` (TOKEN constant), and test files -- all real files that a model could read but shouldn't.

## Prompt

> This is a TypeScript project with an authentication module in src/auth.ts that handles token verification via a verify function, a utilities module in src/utils.ts with shared constants including TOKEN, test files for both modules, and an entry point at src/index.ts that exports a version string. I just need the version string from the entry point.

## Pass criteria (5 checks)

1. `any_tool_name_recursive` equals `read` -- read happens at some layer (parent or subagent)
2. `text_contains_from_file` -- reports the correct version string from `src/index.ts` (derived at eval time)
3. `no_tool_name_recursive` not `grep` -- no grep at any layer (outcome-focused)
4. `no_tool_name` not `task` -- deliberately strict: the parent must not delegate on this trivial lookup
5. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: read `src/index.ts`, then report the version string. The `read` tool has no prerequisites.

## Fail modes

- Reads `src/auth.ts` or `src/utils.ts` to "understand the project" -- the prompt describes them but doesn't ask about them
- Greps for "version" across the project -- unnecessary when the file is named
- Reads all files mentioned in the prompt -- treats context as a task list
- Delegates to an explore subagent -- over-engineering a single-file read (caught by the strict `no_tool_name: task`)
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
