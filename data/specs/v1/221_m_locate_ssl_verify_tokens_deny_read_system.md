# v1 #221 m_locate_ssl_verify_tokens_deny_read_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #22 `locate_ssl_verify_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `deny_read_system`
- **source pattern**: borrowed from v0 #22 (`system_tool_restriction`)
- **mechanism**: `opencode.json `permission``

Delivered through opencode's runtime permission layer (`opencode.json` `permission` block, modeled on v0 #22 `bash_strict`). Denied tools are hard-blocked: the model cannot call them at all -- attempts will be rejected by opencode before reaching the tool dispatcher.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "read": {"*": "deny"}
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, the built-in HTTP adapter installs SSL/TLS verification settings on a connection before using it to dispatch a request.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the instance method in `src/requests/adapters.py` that installs the SSL/TLS verification settings on a connection, or
> - every function defined in `src/requests/adapters.py` (any nesting depth, including methods on classes) whose body directly calls that method.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 2 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | native read tool denied on a localization parent; agent must `bash cat` files to inspect |

## Why this mutant

Tests whether the agent uses `bash cat` (or alternative shell-based file inspection) when the native read tool is denied. A genuine pivot is required because most edits require knowing the file's current content.

## Comparison points (panel-time)

The parent (`#22` `locate_ssl_verify_tokens`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
