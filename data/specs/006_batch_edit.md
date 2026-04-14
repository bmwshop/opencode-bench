# #6 batch_edit

## Category

efficiency

## Project

default

## Contract

completion

## Surface

tools

## Capability

Tool call efficiency -- multi-edit without unnecessary steps. When the prompt provides exact old and new strings for multiple replacements in the same file, the model should minimise the total number of tool calls. This tests whether the model can identify the most concise approach to multi-step mutations.

## Design rationale

A common pattern in agent sessions is making several changes to one file. The most efficient approach is a single `bash` call with `sed` performing both replacements. A less efficient but still acceptable approach is `read` + two `edit` calls (3 total), since the `edit` tool requires a prior read (enforced by `filetime.assert` at runtime). Anything beyond 3 calls (e.g. read-edit-read-edit or post-edit verification reads) is excessive.

The test is **tool-agnostic**: it does not prescribe which tool to use. Instead it scores purely on call count via `tool_count_score`. This avoids conflicts with the `edit` tool's read-before-edit runtime enforcement -- the model can freely choose the tool that best fits the efficiency goal.

| Strategy | Calls | Score |
|---|---|---|
| 1 bash call with `sed` doing both replacements | 1 | optimal |
| 2 bash calls (one per replacement) | 2 | acceptable |
| read + 2 edits | 3 | acceptable (at limit) |
| read + edit + read + edit | 4+ | fail |

## Setup

Uses the default project. The file `src/auth.ts` contains:

```ts
import { TOKEN } from './utils'

// NEEDLE_f9c2
// MARKER: b7e1d930
export function verify(input: string) {
  return input === TOKEN
}
```

Both `// NEEDLE_f9c2` and `// MARKER: b7e1d930` are exact strings the model can use directly.

## Prompt

> In src/auth.ts, make two changes: (1) replace `// NEEDLE_f9c2` with `// NEEDLE_updated`, and (2) replace `// MARKER: b7e1d930` with `// MARKER: updated`. Both old strings are exact -- do it as concisely as possible.

## Pass criteria (4 checks)

1. `max_tool_count` max 3 -- at most 3 tool calls
2. `tool_count_score` optimal 1, limit 3 -- 1 bash call is optimal, up to 3 acceptable
3. `file_regex` `src/auth.ts` matches `NEEDLE_updated` -- first replacement applied on disk
4. `file_regex` `src/auth.ts` matches `MARKER: updated` -- second replacement applied on disk

## Shortest path

**1 tool call**: a single `bash` call with `sed` performing both replacements. The `bash` tool has no prerequisites. `max_tool_count` allows up to 3.

## Fail modes

- Uses 4+ tool calls (read-edit-read-edit or similar) -- excessive procedural overhead
- Makes only one replacement and misses the second
- Calls read between the two edits to "verify" the first change
- Fails to apply the replacements on disk (tool errors out)
