# v1 #205 m_default_hooks_deny_full_bash_only_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #58 `edit_default_hooks_include_request` (`code_editing`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

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

> Modify the function `default_hooks` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the tiny hooks module that declares the list of hook event names and the helper `default_hooks` that returns a default, empty hook registry. The file already defines a module-level list of supported hook names; the default hook registry is built as a dict comprehension over that list.
> 
> Behavior contract:
> 
> Modify the function `default_hooks` and its supporting module-level state (declared in the tiny hooks module of the `requests` package) so that the hook system supports a `'request'` event in addition to the existing `'response'` event:
> 
> - The module-level list of hook event names (currently exactly `['response']`) must become exactly `['response', 'request']`, in that order, with length `2`.
> - `default_hooks()` must continue to return a `dict` whose `'response'` key maps to `[]` (the empty list).
> - `default_hooks()` must additionally have a `'request'` key that maps to `[]`.
> - `len(default_hooks())` must equal exactly `2`.
> 
> The minimal change is to extend the module-level list and let the existing dict comprehension propagate the new key automatically. Do NOT hard-code the `'request'` key directly in the comprehension or append a non-empty default callback list.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (4 checks)

| # | type | description |
|---|------|-------------|
| 1 | `exec_assert` | function `default_hooks` in `src/requests/hooks.py` satisfies all 6 behavioral assertions (regression + new-behavior) |
| 2 | `call_schema_valid` | all tool calls match opencode schemas |
| 3 | `no_tool_name_recursive` | deny-full bash-only system: only bash is allowed; all native tools and delegation are blocked |
| 4 | `any_tool_name_recursive` | must use bash to apply the edit (e.g. via sed/python -c) |
