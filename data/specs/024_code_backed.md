# #24 code_backed

- **Category:** skill
- **Project:** skill_code

## Capability

Code-backed skill execution. Skills in opencode can include sibling code files alongside the `SKILL.md`. This test verifies the model loads a skill that references an executable script (`validate.sh`), runs it via bash, and reports the output. The skill's instructions tell the model to run a validation script located in the skill's own directory.

## Setup

The project has a skill named `validate` at `.opencode/skills/validate/SKILL.md` with instructions:
1. Run the validation script `validate.sh` located in this skill's directory
2. Report the validation code from the script output to the user

The sibling file `validate.sh` is an executable script that outputs `VALID_x7k2m9`.

## Prompt

> Validate the project.

## Pass criteria

- Model calls the `skill` tool (loads the validate skill)
- Model calls the `bash` tool (runs the validation script)
- Response text includes the validation code `VALID_x7k2m9`

## Fail modes

- Doesn't load the skill -- tries to validate using its own judgment
- Loads the skill but doesn't run the script (just describes what it would do)
- Runs the script but doesn't report the validation code in the response
- Can't locate the script because it doesn't understand skill directory structure
