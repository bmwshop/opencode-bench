# v1 #406 skill_style_encoding_httpx

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **style-encoding**
- scope_kind: **single-skill**
- answer_shape: **file-content-match**
- unique_trait: encoding-convention rules on httpx

## Repo

`httpx` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `encoding-convention`

`projects/v1/skills/406/.opencode/skills/encoding-convention/SKILL.md`:

```text
---
name: encoding-convention
description: Bytes-decoding convention for this project. Use whenever you author a new helper that decodes bytes to str.
---

In this `httpx` project, every NEW helper that decodes bytes to str must follow
these conventions:

1. Use UTF-8 encoding with strict error handling. The exact decode call must be:
   ```python
   value.decode('utf-8', errors='strict')
   ```
   Do NOT use the default `value.decode()` (which silently allows incorrect bytes
   under some platform configurations). Do NOT use `errors='ignore'` or `'replace'`.

2. Each helper that performs a decode must be preceded by a single-line comment
   beginning with `# ENCODING:` documenting the encoding choice. Example:

   ```python
   # ENCODING: utf-8 strict
   def bytes_url_to_str(value):
       return value.decode('utf-8', errors='strict')
   ```

Both rules apply together. Apply them to any new helper file you create.
```


## Prompt

> Create a small helper at `httpx/_url_conv.py` that converts a bytes URL into a Python string.
> 
> The project ships a style-rules skill defining encoding conventions any new bytes-handling helper must follow. Use it.

## Pass criteria (6 checks)

| # | type | description |
|---|------|-------------|
| 1 | `any_tool_param_value_recursive` | model loaded the right skill |
| 2 | `any_tool_name` | model used the skill tool at the parent layer |
| 3 | `any_tool_name` | model wrote the _url_conv.py file |
| 4 | `file_regex` | uses prescribed strict UTF-8 decode |
| 5 | `file_regex` | file has the prescribed encoding-comment marker |
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

Style tier-A on httpx. Skill prescribes UTF-8 strict decoding + ENCODING: comment for any new bytes-handling helper. Tests subtle style-rule discipline (errors='strict' is non-default).
