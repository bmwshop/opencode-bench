# #15 code_backed

## Category

skill

## Contract

completion

## Surface

skills

## Capability

Code-backed skill execution. Skills in opencode can include sibling code files alongside the `SKILL.md`, typically under a `scripts/` subdirectory. This test verifies the model loads a skill that references a Python script (`scripts/validate.py`) via a relative path, resolves the path using the skill's base directory, runs it via bash, and reports the output.

## Setup

The project has a skill named `validate` at `.opencode/skills/validate/SKILL.md` with instructions:
1. Run the validation script at `scripts/validate.py`
2. Report the validation code from the script output to the user

The file `scripts/validate.py` is a Python script that outputs a validation code (a `VALID_` prefixed UUID). The skill tool output provides the base directory and states "Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory."

## Prompt

> Validate the project.

## Pass criteria (6 checks)

1. `any_tool_name_recursive` equals `skill` -- skill is invoked at some layer (parent or subagent)
2. `any_tool_param_value_recursive` `skill.name` equals `validate` -- the correct skill is loaded, at any layer
3. `any_tool_name_recursive` equals `bash` -- bash happens at some layer
4. `any_tool_param_regex_recursive` `bash.command` matches `validate\.py` -- some bash call runs validate.py
5. `text_contains_from_file` -- response reports the validation code from `validate.py` (derived at eval time)
6. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**2 tool calls**: `skill` (with `name: "validate"`), then `bash` to run `scripts/validate.py`. Both are required by checks. No tool call checks constrain the upper bound.

## Fail modes

- Doesn't load the skill -- tries to validate using its own judgment
- Loads the skill but doesn't run the script (just describes what it would do)
- Runs `echo` with the validation code instead of `scripts/validate.py` -- fakes the output without running the actual script
- Runs the script but doesn't report the validation code in the response
- Can't resolve the relative path `scripts/validate.py` from the skill's base directory
- Subagent sidecar missing -- `_recursive` checks surface this as `subagent-missing`
