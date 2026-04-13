# #6 batch_edit

## Category

efficiency

## Project

default

## Capability

Tool call efficiency -- multi-edit without intermediate reads. When the prompt provides exact old and new strings for multiple replacements in the same file, the model should chain edit calls back-to-back without reading the file first or between edits. This tests whether the model avoids procedural waste on multi-step mutations.

## Design rationale

A common pattern in agent sessions is making several changes to one file. An efficient model issues N edit calls. An inefficient one reads the file first ("to verify"), then edits, then reads again between edits ("to check"), inflating the tool call count from 2 to 4-5.

This differs from #8 (`direct_edit`) which tests a single edit. Here, the model must demonstrate that it can chain *two* edits without inserting reads between them. The `tool_count_score` with optimal=2 allows distinguishing "added one read" (3 calls, acceptable) from "read-edit-read-edit" (4+ calls, fail).

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

Both `// NEEDLE_f9c2` and `// MARKER: b7e1d930` are exact strings the model can use as `oldString` values.

## Prompt

> In src/auth.ts, make two changes: (1) replace `// NEEDLE_f9c2` with `// NEEDLE_updated`, and (2) replace `// MARKER: b7e1d930` with `// MARKER: updated`. Both old strings are exact -- go ahead.

## Pass criteria (6 checks)

1. `min_tool_count` `edit` >= 2 -- makes at least two edit calls
2. `max_tool_count` max 2 -- exactly two tool calls total (no reads)
3. `no_tool_name` not `read` -- does not read the file
4. `tool_count_score` optimal 2, limit 3 -- 2 calls is optimal, 3 acceptable, 4+ fails
5. `file_regex` `src/auth.ts` matches `NEEDLE_updated` -- first replacement applied on disk
6. `file_regex` `src/auth.ts` matches `MARKER: updated` -- second replacement applied on disk

## Fail modes

- Reads auth.ts before editing -- the exact old strings are provided
- Reads auth.ts between the two edits to "verify" the first change -- unnecessary intermediate check
- Makes only one edit call and misses the second replacement
- Uses `bash sed` instead of the native edit tool
