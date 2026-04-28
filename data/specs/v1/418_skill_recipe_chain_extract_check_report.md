# v1 #418 skill_recipe_chain_extract_check_report

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-chain-extract-iter-write**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: read -> 8 greps -> write coverage via SKILL.md (sister of #304)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `chain-extract-check-report`

`projects/v1/skills/418/.opencode/skills/chain-extract-check-report/SKILL.md`:

```text
---
name: chain-extract-check-report
description: Extract-check-report workflow that audits whether each function from one file is referenced from another. Use for cross-module-coverage audits.
---

When asked to check whether each function in one file is referenced
from another:

1. **Read** the source file (e.g. `src/requests/api.py`) to identify
   the top-level function names.
2. For EACH identified function name, issue ONE separate `grep` call
   searching the consumer file (e.g. `src/requests/sessions.py`) for
   the function name. Issue exactly N grep calls (one per function),
   in the order the functions appear in the source.
3. Write `coverage.md` at the repo root with one line per function in
   the same order:

   ```
   <function_name>: used        (if grep returned >=1 match)
   <function_name>: unused      (otherwise)
   ```

No `glob` and no extra `read` calls beyond step 1.
```


## Prompt

> For each top-level function in `src/requests/api.py`, determine whether `src/requests/sessions.py` references it. Write the results to `coverage.md` at the repo root.
> 
> The project ships a skill that defines the exact procedure (which tools to call, in what order); use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `tool_before` | read precedes greps |
| 4 | `tool_before` | greps precede write |
| 5 | `file_regex` | request marked used |
| 6 | `file_regex` | get marked used |
| 7 | `file_regex` | delete marked used |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |

## Comparison

This sample's parent is **#304** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #304. The 8-grep-per-function recipe lives in the skill; user prompt only states the deliverable goal.
