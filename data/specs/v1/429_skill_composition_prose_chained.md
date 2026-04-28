# v1 #429 skill_composition_prose_chained

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **composition-prose-chain**
- scope_kind: **multi-skill-invocation**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: user prompt names one skill; that skill's body prescribes loading a second skill

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `super-review`

`projects/v1/skills/429/.opencode/skills/super-review/SKILL.md`:

```text
---
name: super-review
description: Comprehensive code review skill that handles the full review workflow itself. Use when the user asks for a full code review and points to this skill specifically.
---

When asked to perform a comprehensive review:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

The review must include the `# Review:` heading and the `## TODO Count:`
subheading exactly as shown. This skill is self-contained and does not
require invoking other skills.
```


## Prompt

> Use the `super-review` skill to review `src/requests/auth.py` and write a `review.md` summary at the repo root.
> 
> Follow the skill's prescribed steps exactly, including any sub-skills it tells you to load.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | super-review skill loaded |
| 2 | `any_tool_name` | model produced the review artifact |
| 3 | `file_regex` | review.md has the prescribed heading |
| 4 | `file_regex` | review.md has the TODO Count subheading |
| 5 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Prose-chain composition. The skill body itself prescribes the recipe (read + count + write); the model just needs to load super-review and follow it. Tests skill body-following on a multi-step procedure (analog to Tier A workflow but framed as composition).
