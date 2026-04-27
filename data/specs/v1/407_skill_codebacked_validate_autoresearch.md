# v1 #407 skill_codebacked_validate_autoresearch

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **code-backed-validate**
- scope_kind: **single-skill**
- answer_shape: **stdout-needles**
- unique_trait: validate-train code-backed skill on autoresearch

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `validate-train`

`projects/v1/skills/407/.opencode/skills/validate-train/SKILL.md`:

```text
---
name: validate-train
description: Project validation workflow. Use when asked to validate or check this autoresearch project; runs the bundled validation script and reports its output code.
---

To validate this project:

1. Run the bundled validation script: `scripts/validate.py` (relative to this
   skill's base directory, which the `skill` tool reports back to you on load).

2. The script prints a single line of the form `VALID_<8-hex-chars>` to stdout.
   Capture that token.

3. Report the captured token verbatim to the user in your final reply.

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
```

`projects/v1/skills/407/.opencode/skills/validate-train/scripts/validate.py`:

```python
#!/usr/bin/env python3
"""Trivial validation script for the validate-train skill (sample #407).

Prints a single-line validation token. The token is hard-coded at the pinned
commit so the audit harness can verify the model's response includes it. In a
real validation script this would inspect repo state and emit a derived token;
here we keep it deterministic for the bench.
"""
print("VALID_a8c9f1e2")
```


## Prompt

> Validate this `autoresearch` project and report the validation code in your final reply.
> 
> The project ships a skill that bundles a validation script; use the skill to discover the script and execute it.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model invoked bash to run the script |
| 4 | `any_tool_param_regex` | bash command runs validate.py |
| 5 | `text_contains` | response includes the validation code printed by the script |
| 6 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Code-backed tier-A on autoresearch. Skill ships a sibling Python script that prints a UUID. Tests path-resolution + bash execution + report-output integration. Direct port + tightening of v0 #15.
