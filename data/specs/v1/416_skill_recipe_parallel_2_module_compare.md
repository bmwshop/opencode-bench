# v1 #416 skill_recipe_parallel_2_module_compare

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-parallel-dispatch-2**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: parallel 2-module compare recipe via SKILL.md (sister of #302)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `parallel-2-module-compare`

`projects/v1/skills/416/.opencode/skills/parallel-2-module-compare/SKILL.md`:

```text
---
name: parallel-2-module-compare
description: Two-module API comparison workflow for the requests repo. Use when the user asks to compare the public APIs of Session and HTTPAdapter.
---

When asked to compare two module APIs:

1. **In a single assistant turn**, dispatch TWO `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: read `src/requests/sessions.py` and list the public
     method names of the `Session` class (methods that don't start with
     `_`), in source-file order.
   - Subagent 2: read `src/requests/adapters.py` and list the public
     method names of the `HTTPAdapter` class (methods that don't start
     with `_`), in source-file order.

2. After both return, write `comparison.md` at the repo root with two
   sections:

   ```
   ## Session
   <one method name per line>

   ## HTTPAdapter
   <one method name per line>
   ```

Do NOT call `read`, `grep`, or `glob` directly from the parent; only
the subagents inspect files.
```


## Prompt

> Compare the public APIs of `Session` (in `src/requests/sessions.py`) and `HTTPAdapter` (in `src/requests/adapters.py`). Write a `comparison.md` summary at the repo root.
> 
> The project ships a skill that defines the comparison procedure; use it.

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `parallel_dispatch_count` | 2 task subagents dispatched in one assistant turn |
| 4 | `any_tool_name` | model produced comparison.md |
| 5 | `file_regex` | comparison has Session section |
| 6 | `file_regex` | comparison has HTTPAdapter section |
| 7 | `file_regex` | Session.prepare_request listed |
| 8 | `file_regex` | HTTPAdapter.init_poolmanager listed |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |

## Comparison

This sample's parent is **#302** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #302. The user prompt names the two modules to compare but not the parallel-dispatch shape; that prescription lives in the skill.
