# v1 #404 skill_style_naming_autoresearch

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **style-naming**
- scope_kind: **single-skill**
- answer_shape: **file-content-match**
- unique_trait: naming-convention rules on autoresearch

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `naming-convention`

`projects/v1/skills/404/.opencode/skills/naming-convention/SKILL.md`:

```text
---
name: naming-convention
description: In-house naming convention for new helper files in this project. Use whenever you author a new top-level Python helper.
---

In this `autoresearch` project, every NEW helper file (and every NEW top-level
function added to an existing file) must follow these conventions:

1. Top-level function names must be prefixed with `_az_`. Examples:
   - good: `_az_compute_step_count`, `_az_load_shard`
   - bad: `compute_step_count`, `load_shard`

2. Each function must be preceded by a single-line marker comment `# AZ_HELPER`
   on its own line, immediately above the `def`.

Both rules apply together: a function without the prefix OR without the marker
fails the convention. Apply them to any file you create.
```


## Prompt

> Create a new file `helpers.py` at the repo root that defines a function returning the product of two integers.
> 
> The project ships a style-rules skill that defines the conventions any new helper file must follow in this codebase. Use it.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model wrote the helpers.py file |
| 4 | `file_regex` | function uses the prescribed _az_ prefix |
| 5 | `file_regex` | file has the prescribed marker comment |
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

Style tier-A on autoresearch. Skill defines a fictional in-house naming convention (`_az_` prefix + `# AZ_HELPER` marker). Tests skill-as-style-rules: model must apply skill's conventions to its own output, not just follow a procedural recipe.
