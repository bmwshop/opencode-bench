# v1 #420 skill_recipe_dag_response_attrs

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-dag-overlap**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: two parallel reads -> overlap analysis via SKILL.md (sister of #306)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `dag-response-attrs`

`projects/v1/skills/420/.opencode/skills/dag-response-attrs/SKILL.md`:

```text
---
name: dag-response-attrs
description: Compare two attribute lists from two source files and report their overlap. Use for cross-module attribute-overlap audits.
---

When asked to compare attribute lists from two related files:

1. **In a single assistant turn**, dispatch TWO `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: list the attribute names assigned in the first
     source's relevant scope (e.g. `Response.__init__` self assignments).
   - Subagent 2: list the attribute names assigned in the second
     source's relevant scope (e.g. local-variable assignments inside
     `HTTPAdapter.build_response`).

2. After both return, write the comparison artifact (e.g.
   `attr_overlap.md`) at the repo root with three sections:

   ```
   ## __init__ attrs
   <sorted, one per line>

   ## build_response attrs
   <sorted, one per line>

   ## overlap
   <names appearing in BOTH lists, sorted, one per line>
   ```

Do NOT call `read`, `grep`, or `glob` directly from the parent; only
the subagents inspect files.
```


## Prompt

> Produce an `attr_overlap.md` summary that compares the attributes assigned in `Response.__init__` (in `src/requests/models.py`) vs those assigned in `HTTPAdapter.build_response` (in `src/requests/adapters.py`), highlighting overlap.
> 
> The project ships a skill that defines the procedure; use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `parallel_dispatch_count` | 2 task subagents dispatched in one assistant turn |
| 4 | `file_regex` | report has __init__ attrs section |
| 5 | `file_regex` | report has build_response attrs section |
| 6 | `file_regex` | report has overlap section |
| 7 | `file_regex` | status_code attr listed |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |

## Comparison

This sample's parent is **#306** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #306. Two parallel reads + an overlap-analysis aggregation. Skill prescribes the sectioned output format.
