# #5 wrong_lead

## Category

distractor

## Project

default

## Capability

Distractor resistance -- misleading causal narrative. The prompt describes a bug in `src/auth.ts` (verify returning false) and then identifies the root cause as the TOKEN constant in `src/utils.ts`. The actual task is simply to read the TOKEN value from utils.ts. The model must resist the temptation to read auth.ts first to "understand the bug" when the prompt already provides the diagnosis.

## Design rationale

Users frequently explain *why* before stating *what*. A diagnostic narrative like "function X in file A is broken because of value Y in file B -- what is Y?" creates a strong pull to read file A first. But the causal chain is already provided by the user; the model only needs to check file B.

This differs from #3 (`focused_read`) which tests file-listing noise, and from #4 (`verbose_context`) which tests architectural prose noise. Here, the distraction is a *causal reasoning chain* that tempts the model into investigative behavior.

## Setup

Uses the default project. The file `src/utils.ts` contains:

```ts
export const TOKEN = "abc123"
```

The file `src/auth.ts` contains a `verify` function that imports and compares against TOKEN. The prompt describes the auth.ts bug but the task only requires reading utils.ts.

## Prompt

> The verify function in src/auth.ts is returning false for valid inputs. I think the issue is the TOKEN constant in src/utils.ts. What is TOKEN currently set to?

## Pass criteria (5 checks)

1. `any_tool_name` equals `read` -- uses the read tool
2. `any_tool_param_regex` `read.filePath` matches `utils` -- reads utils.ts (the target file)
3. `text_contains` `abc123` -- reports the correct TOKEN value
4. `max_tool_count` max 2 -- at most 2 tool calls total
5. `no_tool_name` not `grep` -- does not grep when the file is already named

## Fail modes

- Reads `src/auth.ts` first to "investigate" the verify bug -- the user already diagnosed the issue
- Reads both auth.ts and utils.ts -- wastes a call on auth.ts
- Greps for "TOKEN" across the project -- unnecessary when the file is specified
- Tries to fix the bug instead of just reporting the current value
