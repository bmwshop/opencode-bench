# v1 #410 skill_discovery_two_skill_workspace

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **discovery-2-skills**
- scope_kind: **multi-skill-workspace**
- answer_shape: **tool-presence-or-absence**
- unique_trait: two-skill workspace; correct skill must be selected by description

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `review-flow`

`projects/v1/skills/410/.opencode/skills/review-flow/SKILL.md`:

```text
---
name: review-flow
description: Code review workflow for this repository. Use when the user asks to review a code file for outstanding TODOs and produce a review document.
---

When asked to review a code file in this project, follow these steps in order:

1. Read the target file using the `read` tool.
2. Count the TODO comments (lines containing the literal `TODO`) in the file.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

The `# Review:` heading and `## TODO Count:` subheading are required substrings.
```

### `dependency-audit`

`projects/v1/skills/410/.opencode/skills/dependency-audit/SKILL.md`:

```text
---
name: dependency-audit
description: Third-party dependency audit workflow. Use when the user asks to audit which third-party packages this project depends on and what versions are pinned.
---

When asked to audit third-party dependencies:

1. Read the project's dependency file (`setup.py`, `pyproject.toml`, or
   `requirements.txt`) to enumerate declared third-party packages.
2. For each dependency, record its declared version constraint.
3. Write `dependencies.md` at the repo root with this format:

   ```
   # Dependencies
   - <package>: <version-constraint>
   ...
   ```

This skill is for DEPENDENCY audits, not code reviews. If the user is asking
to review CODE for TODOs or issues, this is the wrong skill -- the project
ships a `review-flow` skill for that.
```


## Prompt

> Review `src/requests/sessions.py` for outstanding TODO comments and write a `review.md` summary at the repo root.
> 
> The project has multiple skills installed; pick whichever one matches the task and use it.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model selected the review-flow skill (correct match for the task) |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model produced the review artifact |
| 4 | `file_regex` | review.md has the skill-prescribed heading |
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

Tier-B discovery hello-world: 2 skills installed (review-flow + dependency-audit), only review-flow matches the user task. v1 doesn't strictly forbid loading the distractor (that's tier-D); the test just verifies the correct skill loaded. Future #411-#414 add more distractors and tighten the negation.
