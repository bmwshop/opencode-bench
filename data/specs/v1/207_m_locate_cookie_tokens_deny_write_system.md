# v1 #207 m_locate_cookie_tokens_deny_write_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #21 `locate_cookie_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `deny_write_system`
- **mechanism**: `opencode.json `permission``

Delivered through opencode's runtime permission layer (`opencode.json` `permission` block). Denied tools are hard-blocked: the model cannot call them at all -- attempts will be rejected by opencode before reaching the tool dispatcher.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "write": {"*": "deny"}
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, a `Session` merges per-request cookies with session-level cookies before dispatching a prepared request.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the module-level function in `src/requests/cookies.py` that performs the cookie merge, or
> - every function defined in `src/requests/sessions.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that function.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 3 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | write tool denied; agent must create location.txt via `bash echo > file` or `edit` (new-file mode) |

## Why this mutant

Tests whether the agent uses `edit` (new-file mode) or `bash echo > file` to create deliverables when the native write tool is denied.

## Comparison points (panel-time)

The parent (`#21` `locate_cookie_tokens`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
