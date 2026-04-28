# v1 #421 skill_recipe_iter_def_count

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-iter-bash-foreach**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: for-each-file bash grep -c via SKILL.md (sister of #307)

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `iter-def-count`

`projects/v1/skills/421/.opencode/skills/iter-def-count/SKILL.md`:

```text
---
name: iter-def-count
description: For-each-file def-count audit using bash grep. Use when the user asks to count `def` keyword occurrences across a list of Python files.
---

When asked to count `def ` keyword occurrences across a list of files:

1. For EACH file in the list, issue ONE separate `bash` call running
   `grep -c "def " <file>`. Issue exactly N bash calls (one per file),
   in the same order as the file list.

2. After all bash calls return, write `def_count.md` at the repo root
   with N lines, in the same order:

   ```
   <file_path>: <integer count>
   ```

Use the `bash` tool — NOT the `grep` tool — for the per-file counting.
No `read`, no `glob`.
```


## Prompt

> Count the number of `def ` keyword occurrences in each of these files: `src/requests/adapters.py`, `src/requests/auth.py`, `src/requests/hooks.py`, `src/requests/sessions.py`. Write the results to `def_count.md` at the repo root, one line per file.
> 
> The project ships a skill that defines the exact procedure (which tool to use, how to iterate); use it.

## Pass criteria (8 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `min_tool_count` | at least 4 bash calls (one per file) |
| 4 | `any_tool_name` | model produced def_count.md |
| 5 | `file_regex` | adapters.py count = 20 |
| 6 | `file_regex` | hooks.py count = 2 |
| 7 | `file_regex` | sessions.py count = 28 |
| 8 | `call_schema_valid` | all tool calls match opencode schemas |

## Comparison

This sample's parent is **#307** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #307. The 'one bash grep -c per file' iteration recipe is in the skill; user prompt names the 4 files but not the per-file iteration.
