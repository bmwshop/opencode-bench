# v1 #410 skill_discovery_two_skill_workspace

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

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
