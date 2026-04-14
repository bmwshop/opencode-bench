# #15 code_backed

## Category

skill

## Project

skill_code

## Contract

completion

## Surface

skills

## Capability

Code-backed skill execution. Skills in opencode can include sibling code files alongside the `SKILL.md`. This test verifies the model loads a skill that references an executable script (`validate.sh`), runs it via bash, and reports the output. The skill's instructions tell the model to run a validation script located in the skill's own directory.

## Setup

The project has a skill named `validate` at `.opencode/skills/validate/SKILL.md` with instructions:
1. Run the validation script `validate.sh` located in this skill's directory
2. Report the validation code from the script output to the user

The sibling file `validate.sh` is an executable script that outputs `VALID_x7k2m9`.

## Prompt

> Validate the project.

## Pass criteria (5 checks)

1. `any_tool_name` equals `skill` -- model invokes the skill tool
2. `any_tool_param_value` `skill.name` equals `validate` -- loads the correct skill
3. `any_tool_name` equals `bash` -- model runs a bash command
4. `any_tool_param_regex` `bash.command` matches `validate\.sh` -- bash command runs validate.sh
5. `text_contains` `VALID_x7k2m9` -- response reports the validation code

## Shortest path

**2 tool calls**: `skill` (with `name: "validate"`), then `bash` to run `validate.sh`. Both are required by checks. No tool call checks constrain the upper bound.

## Fail modes

- Doesn't load the skill -- tries to validate using its own judgment
- Loads the skill but doesn't run the script (just describes what it would do)
- Runs `echo VALID_x7k2m9` instead of `validate.sh` -- fakes the output without running the actual script
- Runs the script but doesn't report the validation code in the response
- Can't locate the script because it doesn't understand skill directory structure
