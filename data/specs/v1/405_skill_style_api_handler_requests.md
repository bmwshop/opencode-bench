# v1 #405 skill_style_api_handler_requests

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **style-api**
- scope_kind: **single-skill**
- answer_shape: **file-content-match**
- unique_trait: api-style handler conventions on requests

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `api-style`

`projects/v1/skills/405/.opencode/skills/api-style/SKILL.md`:

```text
---
name: api-style
description: API handler conventions for this project. Use whenever you author a new API handler / endpoint helper.
---

In this `requests` project, every NEW API-handler function must follow these
conventions:

1. Function names must be prefixed with `handle_`. Examples:
   - good: `handle_register`, `handle_login`, `handle_logout`
   - bad: `register`, `login_handler`, `do_login`

2. Each handler function must be preceded by a `# API_HANDLER` marker comment
   on its own line, immediately above the `def`.

3. Handlers should return a 2-tuple `(ok: bool, data: dict)` where `ok` is the
   success flag and `data` is the response payload.

All three rules apply together. Apply them to any handler file you create.
```


## Prompt

> Create `src/requests/handlers.py` with a function that handles a user-registration payload (no real network logic; just validate the shape).
> 
> The project ships a style-rules skill defining the conventions any new API-handler file must follow. Use it.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model wrote the handlers.py file |
| 4 | `file_regex` | function uses the prescribed handle_ prefix |
| 5 | `file_regex` | file has the prescribed marker comment |
| 6 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Style tier-A on requests. Skill prescribes API-handler conventions; user creates a new handler. Triple distinct from #404 by template.
