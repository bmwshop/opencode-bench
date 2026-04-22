# #6 batch_edit

## Category

efficiency

## Contract

completion

## Surface

tools

## Capability

Tool call efficiency -- multi-edit without unnecessary steps. When the prompt provides exact old and new strings for multiple replacements in the same file, the model should minimise the total number of tool calls. This tests whether the model can identify the most concise approach to multi-step mutations.

## Design rationale

A common pattern in agent sessions is making several changes to one file. Opencode's bash tool guidance explicitly says "DO NOT use it for file operations (reading, writing, editing) - use the specialized tools instead" and "Edit files: Use Edit (NOT sed/awk)". Therefore the optimal path uses the `edit` tool, which requires a prior `read` (enforced by `filetime.assert` at runtime).

| Strategy | Calls | Score |
|---|---|---|
| read + 2 edits | 3 | optimal |
| read + edit + read + edit | 4+ | fail |

## Setup

The file `src/auth.ts` contains a NEEDLE comment and a MARKER comment (both with UUID values), along with the verify function. The prompt provides the exact old and new strings for both replacements.

## Prompt

> In src/auth.ts, make two changes: (1) replace the NEEDLE comment with `// NEEDLE_updated`, and (2) replace the MARKER comment with `// MARKER: updated`. Both old strings are provided exactly in the prompt -- do it as concisely as possible.

## Pass criteria (5 checks)

1. `max_tool_count_recursive` max 3 -- at most 3 tool calls across all layers (parent + any `task` subagents)
2. `tool_count_score_recursive` optimal 3, limit 3 -- read + 2 edits at any layer (opencode discourages bash for file edits)
3. `file_regex` `src/auth.ts` matches `NEEDLE_updated` -- first replacement applied on disk
4. `file_regex` `src/auth.ts` matches `MARKER: updated` -- second replacement applied on disk
5. `call_schema_valid` -- all tool calls (parent + subagents) validate against `data/tool_schemas.json`

## Shortest path

**3 tool calls**: `read src/auth.ts` then two `edit` calls (one per replacement). The `edit` tool requires a prior read (`filetime.assert`). Opencode discourages `bash` for file edits.

## Fail modes

- Uses 4+ tool calls (read-edit-read-edit or similar) -- excessive procedural overhead
- Delegates the edits to a `task` subagent whose own tool calls (the subagent's read + edit + edit + any extras) push the total over 3 -- the efficiency ceiling applies across all layers, so delegation is not an escape hatch
- Makes only one replacement and misses the second
- Calls read between the two edits to "verify" the first change
- Fails to apply the replacements on disk (tool errors out)
