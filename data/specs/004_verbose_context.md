# #4 verbose_context

## Category

distractor

## Project

default

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

Uses the default project. The file `src/index.ts` contains:

```ts
// MARKER: 8f3a2b1c
export const version = '1.0.0'
```

The prompt describes `src/auth.ts` (verify function, token verification), `src/utils.ts` (TOKEN constant), and test files -- all real files that a model could read but shouldn't.

## Prompt

> This is a TypeScript project with an authentication module in src/auth.ts that handles token verification via a verify function, a utilities module in src/utils.ts with shared constants including TOKEN, test files for both modules, and an entry point at src/index.ts that exports a version string. I just need the version string from the entry point.

## Pass criteria (5 checks)

1. `any_tool_name` equals `read` -- uses the read tool
2. `text_contains` `1\.0\.0` -- reports the correct version string
3. `max_tool_count` max 2 -- at most 2 tool calls total
4. `no_tool_name` not `grep` -- does not grep when the target file is named
5. `no_tool_name` not `task` -- does not delegate unnecessarily

## Shortest path

**1 tool call**: read `src/index.ts`, then report the version string. The `read` tool has no prerequisites. `max_tool_count` allows up to 2.

## Fail modes

- Reads `src/auth.ts` or `src/utils.ts` to "understand the project" -- the prompt describes them but doesn't ask about them
- Greps for "version" across the project -- unnecessary when the file is named
- Reads all files mentioned in the prompt -- treats context as a task list
- Delegates to an explore subagent -- over-engineering a single-file read
