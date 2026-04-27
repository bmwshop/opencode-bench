# v1 #226 m_locate_auth_prep_tokens_deny_glob_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #31 `locate_auth_prep_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `deny_glob_system`
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
    "glob": {"*": "deny"}
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, a `PreparedRequest` attaches HTTP auth credentials to itself after body preparation, delegating to the user's auth callable (e.g. `HTTPBasicAuth`) and re-running Content-Length preparation if the auth hook mutates the body.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the instance method on `PreparedRequest` in `src/requests/models.py` that attaches the auth credentials to the prepared request, or
> - every function defined in `src/requests/models.py` or `src/requests/sessions.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that method.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 3 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | glob denied on an easy localization parent (parent diversity vs #208 hard) |

## Why this mutant

Tests whether the agent pivots to `bash find` or alternative discovery strategies when the native glob tool is denied.

## Comparison points (panel-time)

The parent (`#31` `locate_auth_prep_tokens`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
