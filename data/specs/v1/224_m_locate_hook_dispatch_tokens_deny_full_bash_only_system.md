# v1 #224 m_locate_hook_dispatch_tokens_deny_full_bash_only_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #26 `locate_hook_dispatch_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "bash": "allow",
    "read": {"*": "deny"},
    "edit": {"*": "deny"},
    "glob": {"*": "deny"},
    "grep": {"*": "deny"},
    "task": {"*": "deny"},
    "todowrite": "deny"
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, a module-level helper fires the registered user-hooks for a given event key, passing the event data to each hook callable and replacing the data with the callable's return value when non-None.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the module-level helper in `src/requests/hooks.py` that performs this hook dispatch, or
> - every function defined in `src/requests/hooks.py` or `src/requests/sessions.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that helper.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (4 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 2 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | deny-full bash-only system on a localization parent; only bash is allowed |
| 4 | `any_tool_name_recursive` | agent must use bash to search and create location.txt |
