# #5 wrong_lead

## Category

distractor

## Contract

completion

## Surface

tools

## Capability

Distractor resistance -- misleading causal narrative. The prompt describes a bug in `src/auth.ts` (verify returning false), mentions the user has already inspected the logic, and then asks about the TOKEN value in `src/utils.ts`. The phrase "before I dig into auth.ts further" subtly nudges the model toward reading auth.ts. The model must resist this pull and go straight to utils.ts.

## Design rationale

Users frequently explain *why* before stating *what*. A diagnostic narrative like "function X in file A is broken, I've checked the logic, maybe value Y in file B changed?" creates a strong pull to read file A first -- especially when the user says "before I dig into auth.ts further," implying auth.ts is the next step. But the causal chain is already provided by the user; the model only needs to check file B.

This differs from #3 (`focused_read`) which tests file-listing noise, and from #4 (`verbose_context`) which tests architectural prose noise. Here, the distraction is a *causal reasoning chain* that tempts the model into investigative behavior.

## Setup

The file `src/utils.ts` contains a TOKEN constant set to a UUID value. The file `src/auth.ts` contains a `verify` function that imports and compares against TOKEN. The prompt describes the auth.ts bug but the task only requires reading utils.ts.

## Prompt

> The verify function in src/auth.ts is returning false for valid inputs. I've looked at the logic and the comparison seems fine. Maybe the TOKEN value in src/utils.ts changed? Before I dig into auth.ts further, what is TOKEN currently set to?

## Pass criteria (4 checks)

1. `any_tool_name_recursive` equals `read` -- read happens at some layer (parent or subagent)
2. `any_tool_param_regex_recursive` `read.filePath` matches `utils` -- reads utils.ts at some layer, not auth.ts
3. `text_contains_from_file` -- reports the correct TOKEN value from `src/utils.ts` (derived at eval time)
4. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

Note: an earlier version of this sample also required `no grep at any layer`. That check was dropped because `grep TOKEN src/utils.ts` is functionally equivalent to `read src/utils.ts` for answering the question -- both surface the value from the named file without straying to auth.ts. The distractor intent (resisting the pull toward auth.ts) is still enforced by the `any_tool_param_regex_recursive: utils` check on the `read` tool: the model must still do a genuine `read` call (at some layer) against utils.ts. A grep-only trajectory fails `any_tool_name_recursive: read`. A trajectory that reads utils.ts *and also* greps is fine.

## Shortest path

**1 tool call**: read `src/utils.ts`, then report the TOKEN value. The `read` tool has no prerequisites.

## Fail modes

- Reads `src/auth.ts` first -- takes the "before I dig into auth.ts" bait instead of answering the direct question
- Reads both auth.ts and utils.ts -- wastes a call on auth.ts
- Only greps for "TOKEN" without a read call -- fails the `any_tool_name_recursive: read` check (but grep in *addition* to a read is now allowed)
- Tries to fix the bug instead of just reporting the current value
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
