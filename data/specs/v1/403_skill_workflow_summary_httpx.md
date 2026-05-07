# v1 #403 skill_workflow_summary_httpx

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Repo

`httpx` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `summary-flow`

`projects/v1/skills/403/.opencode/skills/summary-flow/SKILL.md`:

```text
---
name: summary-flow
description: Module function-count summary workflow. Use when the user asks for a summary of how many top-level def definitions a Python file contains.
---

When asked to summarize a Python file's function count, follow these steps in order:

1. Read the target file using the `read` tool.
2. Count the lines that begin with `def ` at column 0 (top-level function definitions).
   Do NOT count indented `def ` lines (those are nested inside classes or functions).
3. Write `summary.md` at the repo root with this exact format:

   ```
   # Summary: <basename of target file>
   ## Function Count: <integer>
   ```

The `# Summary:` heading and `## Function Count:` subheading are required substrings;
the hidden grader checks for both. The basename should appear without any directory
prefix (e.g. `_utils.py`, not `httpx/_utils.py`).
```


## Prompt

> Produce a `summary.md` at the repo root reporting the count of top-level `def` definitions in `httpx/_utils.py`.
> 
> The project ships a procedural skill that defines the exact summary format. Use it.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `tool_before` | skill loaded BEFORE the read it prescribes |
| 4 | `any_tool_name` | model produced an artifact |
| 5 | `file_regex` | summary.md has the skill-prescribed heading |
| 6 | `file_regex` | summary.md has the function-count subheading |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |
