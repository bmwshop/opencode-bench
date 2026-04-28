# v1 #419 skill_recipe_dag_two_inputs_one_output

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-dag-2to1**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: two parallel reads -> single combined output via SKILL.md (sister of #305)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `dag-two-inputs-one-output`

`projects/v1/skills/419/.opencode/skills/dag-two-inputs-one-output/SKILL.md`:

```text
---
name: dag-two-inputs-one-output
description: Two-parallel-input, one-output workflow that fetches values from two files and combines them. Use when producing a small "combined values" artifact from two source files.
---

When asked to produce a combined-values artifact from two source files:

1. **In a single assistant turn**, dispatch TWO `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: read the first source file and return the requested
     value (e.g. `EMBEDDING_LR` from `train.py`).
   - Subagent 2: read the second source file and return the requested
     value (e.g. `VOCAB_SIZE` from `prepare.py`).

2. After both return, write the output file (e.g. `combined.py`) at the
   repo root containing exactly two assignment lines (and no others):

   ```
   <FIRST_NAME> = <value from subagent 1>
   <SECOND_NAME> = <value from subagent 2>
   ```

Do NOT call `read`, `grep`, `glob`, or `bash` directly from the parent;
only the subagents inspect files.
```


## Prompt

> Produce a `combined.py` file at the repo root that exports the values of `EMBEDDING_LR` (from `train.py`) and `VOCAB_SIZE` (from `prepare.py`).
> 
> The project ships a skill that defines how to gather the inputs and combine them; use it.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `parallel_dispatch_count` | 2 task subagents dispatched in one assistant turn |
| 4 | `file_regex` | EMBEDDING_LR = 0.6 |
| 5 | `file_regex` | VOCAB_SIZE = 8192 |
| 6 | `call_schema_valid` | all tool calls match opencode schemas |

## Comparison

This sample's parent is **#305** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #305. Two-input-one-output DAG; skill prescribes parallel dispatch and the combined.py format.
