# v1 #414 skill_discovery_no_match_workspace

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `validate-train`

`projects/v1/skills/414/.opencode/skills/validate-train/SKILL.md`:

```text
---
name: validate-train
description: Run the bundled training-pipeline validation script and report its output token. Use when the user asks to validate the autoresearch training pipeline.
---

Run `scripts/validate.py` (relative to the skill base directory) and report the
captured `VALID_<hex>` token. This skill is specific to training-pipeline
validation; it does NOT cover general file analysis or summarization.
```

### `compute-checksum`

`projects/v1/skills/414/.opencode/skills/compute-checksum/SKILL.md`:

```text
---
name: compute-checksum
description: Compute SHA-256 checksum of a file via the bundled checksum script. Use when the user asks for a hash or checksum of a specific file.
---

Run `scripts/checksum.py <path>` (relative to the skill base directory) and
report the resulting `sha256=<hex>` line. This skill is for checksum computation
only; it does not summarize, review, or analyze file contents.
```

### `count-imports`

`projects/v1/skills/414/.opencode/skills/count-imports/SKILL.md`:

```text
---
name: count-imports
description: Count top-level import statements in a Python file via the bundled count-imports script. Use when asked specifically how many imports a Python file has.
---

Run `scripts/count_imports.py <path>` (relative to the skill base directory) and
report the resulting `import_count=<n>` line. This skill counts imports only;
it does not summarize, review, or analyze file contents.
```


## Prompt

> Read `src/requests/utils.py` and write a one-paragraph plain-English summary of the file's purpose to `purpose.md` at the repo root.
> 
> The project has several skills installed; if none of them match this task, just solve it directly with normal tools.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `no_tool_name_recursive` | model did NOT load any skill (none of the installed skills matches the task) |
| 2 | `any_tool_name` | model read the file |
| 3 | `any_tool_name` | model produced the purpose.md artifact |
| 4 | `file_regex` | purpose.md is non-empty |
| 5 | `call_schema_valid` | all tool calls match opencode schemas |
