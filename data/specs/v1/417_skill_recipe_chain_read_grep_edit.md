# v1 #417 skill_recipe_chain_read_grep_edit

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

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
