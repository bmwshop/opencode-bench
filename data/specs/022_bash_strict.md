# #22 bash_strict

## Category

system_tool_restriction

## Project

bash_strict

## Contract

completion

## Surface

permissions

## Capability

System-level tool restriction via permissions. Unlike the prompt-based tests (#12-14), this test uses opencode's permission system to actually hide tools from the model's tool definitions. The `opencode.json` denies `read`, `edit`, `glob`, `grep`, `task`, and `todowrite` -- these tools are removed from the API call entirely. The model never sees them and must work with only `bash`. No custom agent is used -- the default `build` agent runs with the full standard system prompt but a reduced tool set. This tests the model's ability to adapt to a genuinely limited toolset.

## Setup

The `bash_strict` project's `opencode.json` sets root permissions to deny all tools except `bash`. The default `build` agent is used with the standard system prompt. The `src/app.ts` file contains `NEEDLE_abc1`.

## Prompt

> Which file in src/ contains the string NEEDLE_abc1?

## Pass criteria (3 checks)

1. `any_tool_name` equals `bash` -- model uses bash
2. `max_tool_count` max 1 -- exactly one tool call
3. `text_contains` `app\.ts` -- response identifies the correct file

## Shortest path

**1 tool call**: a single `bash` call (e.g. `grep -r NEEDLE_abc1 src/`). Bash is the only tool available. No tool call checks constrain the upper bound.

## Fail modes

- Attempts to call a denied tool (would result in an error or hallucination since the tool doesn't appear in the schema)
- Gives up without trying bash
- Identifies the wrong file

## Difference from #14

Sample #14 tests prompt-based restriction (tools are visible but the model is told not to use them). This sample tests system-level restriction (tools are genuinely removed from the model's context). A model that passes #22 but fails #14 has good tool adaptation but poor instruction following.
