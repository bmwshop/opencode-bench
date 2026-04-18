# #8 direct_edit

## Category

efficiency

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool call efficiency -- performing a text replacement when all information is provided. When the prompt gives the exact file path, old string, and new string, the model should complete the task in as few tool calls as possible. This tests whether the model can identify the most direct path to the result.

## Design rationale

When the prompt provides the exact old and new strings, the model should complete the replacement in as few calls as possible. Opencode's bash tool guidance says "DO NOT use it for file operations (reading, writing, editing) - use the specialized tools instead" and "Edit files: Use Edit (NOT sed/awk)". Therefore the optimal path uses the `edit` tool, which requires a prior `read` (enforced at runtime by `filetime.assert`).

| Strategy | Calls | Score |
|---|---|---|
| read + edit | 2 | optimal |
| read + edit + verify | 3+ | fail |

## Setup

Uses the default project. The file `src/utils.ts` contains a TOKEN constant set to a UUID value.

## Prompt

> In src/utils.ts, replace the exact TOKEN UUID with a new value. Everything you need is in this message -- do it in a single step.

## Pass criteria (3 checks)

1. `max_tool_count` max 2 -- at most 2 tool calls
2. `tool_count_score` optimal 2, limit 2 -- read + edit (opencode discourages bash for file edits)
3. `file_regex` `src/utils.ts` -- file on disk contains the new value from the prompt

## Shortest path

**2 tool calls**: `read src/utils.ts` then `edit` to replace the TOKEN UUID with the new value. The `edit` tool requires a prior read (`filetime.assert`). Opencode discourages `bash` for file edits.

## Fail modes

- Uses 3+ tool calls (read + edit + verify, or grep + edit + read) -- excessive steps
- Calls `edit` without reading first -- tool will error at runtime due to `filetime.assert`
- Uses `grep` to find the old value before replacing -- the prompt already provides it
- Replacement fails on disk (wrong `oldString`, wrong file path, etc.)
