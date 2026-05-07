# v1 #310 prescribed_merge_three_section_summaries

## Category

orchestration

## Repo

`autoresearch` (pinned via `data/v1_repos.json`).

## Prompt

> **In one assistant turn**, dispatch three `task` subagents (`subagent_type=explore`) in parallel. README.md at the repo root has multiple `## ` (level-2) section headings:
> 
> - Subagent 1: read `README.md` and report the heading text (without the leading `## `) of the **first** `##` section.
> - Subagent 2: read `README.md` and report the heading text of the **second** `##` section.
> - Subagent 3: read `README.md` and report the heading text of the **third** `##` section.
> 
> After all three return, write `toc.md` at the repo root with exactly three lines, in this format:
> 
>     1. <heading 1>
>     2. <heading 2>
>     3. <heading 3>
> 
> Do not call `read`, `grep`, or `glob` directly.

## Pass criteria (7 checks)

| # | type | description |
|---|------|-------------|
| 1 | `parallel_dispatch_count` | model must dispatch all 3 task subagents in one assistant turn |
| 2 | `tool_call_count` | exactly 3 subagent dispatches |
| 3 | `no_tool_name` | parent must not inspect README.md directly |
| 4 | `file_regex` | first heading: How it works |
| 5 | `file_regex` | second heading: Quick start |
| 6 | `file_regex` | third heading: Running the agent |
| 7 | `call_schema_valid` | all tool calls match opencode schemas |
