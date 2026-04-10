# #21 bash_strict

## Category

system_tool_restriction

## Project

bash_strict

## Capability

System-level tool restriction via permissions. Unlike the prompt-based tests (#18-20), this test uses opencode's permission system to actually hide tools from the model's tool definitions. The `opencode.json` denies `read`, `edit`, `glob`, `grep`, `task`, and `todowrite` -- these tools are removed from the API call entirely. The model never sees them and must work with only `bash`. This tests the model's ability to adapt to a genuinely limited toolset.

## Setup

The `bash_strict` project's `opencode.json` sets permissions to deny all tools except `bash`. The agent prompt is neutral: "Accomplish tasks using the tools available to you." The `src/app.ts` file contains `NEEDLE_abc1`.

## Prompt (run with `--agent bash_strict`)

> Which file in src/ contains the string NEEDLE_abc1?

## Pass criteria (5 checks)

1. `any_tool_name` equals `bash` -- model uses bash
2. `no_tool_name` not `read` -- does not call the hidden read tool
3. `no_tool_name` not `grep` -- does not call the hidden grep tool
4. `no_tool_name` not `glob` -- does not call the hidden glob tool
5. `text_contains` `app\.ts` -- response identifies the correct file

## Fail modes

- Attempts to call a denied tool (would result in an error or hallucination since the tool doesn't appear in the schema)
- Gives up without trying bash
- Identifies the wrong file

## Difference from #19

Sample #19 tests prompt-based restriction (tools are visible but the model is told not to use them). This sample tests system-level restriction (tools are genuinely removed from the model's context). A model that passes #21 but fails #19 has good tool adaptation but poor instruction following.
