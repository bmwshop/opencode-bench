# v1 #417 skill_recipe_chain_read_grep_edit

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **recipe-chain-3step**
- scope_kind: **single-skill**
- answer_shape: **graph-shape-and-artifact**
- unique_trait: read -> grep -> write chain via SKILL.md (sister of #303)

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `chain-read-grep-edit`

`projects/v1/skills/417/.opencode/skills/chain-read-grep-edit/SKILL.md`:

```text
---
name: chain-read-grep-edit
description: Three-step chain for finding all occurrences of a literal string in a small repo. Use when the user asks to enumerate all occurrences of a pattern.
---

When asked to find every occurrence of a literal string:

1. **Read** the canonical target file using the `read` tool. (For an
   audit of `WEIGHT_DECAY` in autoresearch, the file is `train.py`.)
2. **Grep** for the literal string using the `grep` tool, scoped to the
   repo root.
3. **Write** an `occurrences.md` artifact at the repo root, containing
   one line per match in the format `<filepath>:<line_number>` (sorted
   by line number ascending).

Issue exactly ONE call of each tool, in this exact order: `read`, then
`grep`, then `write`. No other tools.
```


## Prompt

> Find every line in this `autoresearch` repo where the literal string `WEIGHT_DECAY` appears, and write the results to `occurrences.md` at the repo root, one occurrence per line.
> 
> The project ships a skill that defines the exact procedure; use it.

## Pass criteria (9 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | skill loaded at parent layer |
| 3 | `tool_before` | read precedes grep |
| 4 | `tool_before` | grep precedes write |
| 5 | `any_tool_param_regex` | grep searches for WEIGHT_DECAY |
| 6 | `file_regex` | occurrence at train.py:443 listed |
| 7 | `file_regex` | occurrence at train.py:505 listed |
| 8 | `file_regex` | occurrence at train.py:532 listed |
| 9 | `call_schema_valid` | all tool calls match opencode schemas |

## Comparison

This sample's parent is **#303** in the prescriptive orchestration family. Per-model delta `pass_rate(parent) - pass_rate(this)` isolates the SKILL-mediation efficacy signal: same recipe, two delivery channels.

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Tier C sister of #303. User prompt names the goal (find all WEIGHT_DECAY occurrences) but not the chain shape (read -> grep -> write); the skill prescribes that order and the output format.
