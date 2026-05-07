# v1 #415 skill_recipe_parallel_3_facet_audit

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `parallel-3-facet-audit`

`projects/v1/skills/415/.opencode/skills/parallel-3-facet-audit/SKILL.md`:

```text
---
name: parallel-3-facet-audit
description: Three-facet audit workflow for the autoresearch repo. Use when the user asks to audit this repo and produce a structured report.
---

When asked to audit this `autoresearch` repo, follow these steps:

1. **In a single assistant turn**, dispatch THREE `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: read `train.py` and report the four optimizer-related
     module-level constants `EMBEDDING_LR`, `UNEMBEDDING_LR`, `MATRIX_LR`,
     `WEIGHT_DECAY` with their values.
   - Subagent 2: read `train.py` and list the names of all top-level
     classes (e.g. `class GPTConfig`, `class GPT`), in source-file order.
   - Subagent 3: read `prepare.py` and report the tokenizer constants
     `MAX_SEQ_LEN`, `VOCAB_SIZE`, `BOS_TOKEN` with their values.

2. After all three subagents return, write `report.md` at the repo root
   with three sections:

   ```
   # Audit

   ## Optimizer
   EMBEDDING_LR: <v>
   UNEMBEDDING_LR: <v>
   MATRIX_LR: <v>
   WEIGHT_DECAY: <v>

   ## Classes
   <one class name per line>

   ## Tokenizer
   VOCAB_SIZE: <v>
   ```

Do NOT call `read`, `grep`, `glob`, or `bash` directly from the parent;
only the subagents inspect files. The parent agent is responsible for
the final `write`.
```


## Prompt

> Audit this `autoresearch` repo and produce a `report.md` summary at the repo root.
> 
> The project ships a procedural skill that defines exactly how the audit should be done; use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `parallel_dispatch_count` | 3 task subagents dispatched in one assistant turn |
| 4 | `any_tool_name` | model produced report.md |
| 5 | `file_regex` | report has Optimizer section |
| 6 | `file_regex` | EMBEDDING_LR value reported |
| 7 | `file_regex` | VOCAB_SIZE value reported |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |
