# v1 #204 m_unquote_header_value_deny_read_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #54 `edit_unquote_header_value_none_returns_empty` (`code_editing`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

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

> Modify the function `unquote_header_value` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the internal helper `unquote_header_value` that reverses `quote_header_value`, stripping the surrounding double quotes and unescaping `\\` and `\"` inside them. It lives in the `requests` utilities module and is invoked while parsing HTTP list-style headers.
> 
> Behavior contract:
> 
> Modify the function `unquote_header_value` (declared at module scope inside the `requests` utilities module) so that it tolerates `None` inputs without changing any of its existing behaviour:
> 
> - Calling `unquote_header_value(None)` now returns `''` (the empty string).
> - Calling `unquote_header_value(None, is_filename=True)` also returns `''`.
> - All existing behaviour on string inputs is preserved exactly: `unquote_header_value('"hello"')` returns `'hello'`, `unquote_header_value('hello')` returns `'hello'`, `unquote_header_value('')` returns `''`, and `unquote_header_value('"hello world"')` returns `'hello world'`.
> 
> The minimal change is a single early-return guard at the top of the function body; do NOT change the existing quoting/unescaping logic.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `exec_assert` | function `unquote_header_value` in `src/requests/utils.py` satisfies all 6 behavioral assertions (regression + new-behavior) |
| 2 | `call_schema_valid` | all tool calls match opencode schemas |
| 3 | `no_tool_name_recursive` | native read tool is denied; agent must `bash cat` files before constructing the edit |

## Why this mutant

Tests whether the agent uses `bash cat` (or alternative shell-based file inspection) when the native read tool is denied. A genuine pivot is required because most edits require knowing the file's current content.

## Comparison points (panel-time)

The parent (`#54` `edit_unquote_header_value_none_returns_empty`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
