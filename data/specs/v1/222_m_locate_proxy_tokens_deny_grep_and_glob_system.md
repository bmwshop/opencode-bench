# v1 #222 m_locate_proxy_tokens_deny_grep_and_glob_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #23 `locate_proxy_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "grep": {"*": "deny"},
    "glob": {"*": "deny"}
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, a utility helper picks the right proxy URL for a given outgoing request URL out of a proxy-mapping dict.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the module-level utility function in `src/requests/utils.py` that performs this proxy selection, or
> - every function defined in `src/requests/adapters.py` or `src/requests/utils.py` (any nesting depth, including methods on classes) whose body directly calls that utility.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 4 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | both native search tools denied on a localization parent; agent must use bash find/rg or pure read |
