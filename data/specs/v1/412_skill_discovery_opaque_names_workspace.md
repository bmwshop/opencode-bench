# v1 #412 skill_discovery_opaque_names_workspace

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `xyz-001`

`projects/v1/skills/412/.opencode/skills/xyz-001/SKILL.md`:

```text
---
name: xyz-001
description: Code review workflow that scans a target file for outstanding TODO comments and emits a structured review document. Use when the user asks for a code review focused on TODOs.
---

When asked to review a code file in this project, follow these steps in order:

1. Read the target file using the `read` tool.
2. Count the TODO comments in the file.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```
```

### `abc-002`

`projects/v1/skills/412/.opencode/skills/abc-002/SKILL.md`:

```text
---
name: abc-002
description: Third-party dependency audit. Use when asked to enumerate the project's external package dependencies and their version pins.
---

To audit third-party dependencies, read the dependency manifest, enumerate
declared packages with their version constraints, and write `dependencies.md`
at the repo root with one bullet per package.
```

### `def-003`

`projects/v1/skills/412/.opencode/skills/def-003/SKILL.md`:

```text
---
name: def-003
description: Run the bundled validation script and report its output. Use when asked to validate the project or run validation checks.
---

Run `scripts/validate.py` (relative to the skill base directory) via bash and
report the captured `VALID_<hex>` token to the user.
```

### `ghi-004`

`projects/v1/skills/412/.opencode/skills/ghi-004/SKILL.md`:

```text
---
name: ghi-004
description: Encoding-convention rules for new bytes-handling helpers. Use when authoring a new helper that converts between bytes and str.
---

Any new bytes-handling helper must:

- Use `value.decode('utf-8', errors='strict')`.
- Be preceded by a `# ENCODING:` marker comment documenting the encoding choice.
```

### `jkl-005`

`projects/v1/skills/412/.opencode/skills/jkl-005/SKILL.md`:

```text
---
name: jkl-005
description: Naming-convention rules for new top-level helper files. Use when authoring a new helper file or function.
---

Any new top-level helper function must:

- Be prefixed with `_az_` (e.g. `_az_compute_step_count`).
- Be preceded by a `# AZ_HELPER` marker comment.
```


## Prompt

> Review `src/requests/cookies.py` for outstanding TODO comments and write a `review.md` summary at the repo root.
> 
> The project has several skills installed under opaque names; pick whichever description matches the task and use that skill.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model selected the xyz-001 skill (the one whose description matches) |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model produced the review artifact |
| 4 | `file_regex` | review.md has the skill-prescribed heading |
| 5 | `call_schema_valid` | all tool calls match opencode schemas |
