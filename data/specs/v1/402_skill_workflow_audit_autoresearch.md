# v1 #402 skill_workflow_audit_autoresearch

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **workflow-audit**
- scope_kind: **single-skill**
- answer_shape: **artifact-format-match**
- unique_trait: audit-flow procedural workflow on autoresearch

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `audit-flow`

`projects/v1/skills/402/.opencode/skills/audit-flow/SKILL.md`:

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


## Prompt

> Audit the optimizer constants in this `autoresearch` repo and produce an `audit.md` summary at the repo root.
> 
> The project ships a procedural skill that defines exactly how audits should be done in this codebase. Use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `tool_before` | skill loaded BEFORE the read it prescribes |
| 4 | `any_tool_name` | model produced an artifact |
| 5 | `file_regex` | audit.md has the skill-prescribed heading |
| 6 | `file_regex` | audit.md has the Optimizer section |
| 7 | `file_regex` | audit reports the correct EMBEDDING_LR value |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Workflow tier-A on autoresearch. Skill prescribes reading train.py + writing audit.md with two sections (Optimizer, Tokenizer). Distinct from #401 by template (workflow-audit) and target repo. Constants are read from the actual fixture at audit time so the synthesizer can ground-truth the values.
