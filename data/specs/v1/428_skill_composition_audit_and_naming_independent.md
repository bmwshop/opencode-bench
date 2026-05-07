# v1 #428 skill_composition_audit_and_naming_independent

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `audit-flow`

`projects/v1/skills/428/.opencode/skills/audit-flow/SKILL.md`:

```text
---
name: audit-flow
description: Optimizer-constants audit workflow. Use when the user asks to audit the optimizer or learning-rate constants in train.py and produce a report.
---

When asked to audit this project's optimizer constants, follow these steps in order:

1. Read `train.py` using the `read` tool.
2. Identify the four optimizer-related module-level constants:
   - `EMBEDDING_LR`
   - `UNEMBEDDING_LR`
   - `MATRIX_LR`
   - `WEIGHT_DECAY`
3. Identify the tokenizer constants:
   - `VOCAB_SIZE`
   - `MAX_SEQ_LEN`
4. Write `audit.md` at the repo root with this exact format:

   ```
   # Audit: train.py
   ## Optimizer
   EMBEDDING_LR: <v>
   UNEMBEDDING_LR: <v>
   MATRIX_LR: <v>
   WEIGHT_DECAY: <v>
   ## Tokenizer
   VOCAB_SIZE: <v>
   MAX_SEQ_LEN: <v>
   ```

The `# Audit:` heading and `## Optimizer` / `## Tokenizer` subheadings are required;
the hidden grader checks for them. Values must be transcribed from the actual file.
```

### `naming-convention`

`projects/v1/skills/428/.opencode/skills/naming-convention/SKILL.md`:

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

> Two tasks for this `autoresearch` repo:
> 
> 1. Audit the optimizer constants in `train.py` and produce `audit.md` at the repo root.
> 2. Add a new helper function to a new `helpers.py` file at the repo root that returns the product of two integers.
> 
> The project ships separate skills for each task; use both.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | audit-flow skill loaded |
| 2 | `any_tool_param_value_recursive` | naming-convention skill loaded |
| 3 | `min_tool_count` | at least 2 writes (audit.md + helpers.py) |
| 4 | `file_regex` | audit.md has Optimizer section |
| 5 | `file_regex` | helpers.py uses _az_ naming |
| 6 | `file_regex` | helpers.py has AZ_HELPER marker |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |
