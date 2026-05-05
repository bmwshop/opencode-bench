# v1 #202 m_iter_slices_deny_grep_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #51 `edit_iter_slices_require_positive` (`code_editing`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `deny_grep_system`
- **mechanism**: `opencode.json `permission``

Delivered through opencode's runtime permission layer (`opencode.json` `permission` block). Denied tools are hard-blocked: the model cannot call them at all -- attempts will be rejected by opencode before reaching the tool dispatcher.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "grep": {"*": "deny"}
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `src/requests/`; find it by searching the repo for the behavior described.
> 
> > The target is the small pure-Python helper that lazily yields fixed-size chunks of a string (used internally to stream request and response bodies in chunks). It is defined in the `requests` utilities module.
> 
> Behavior contract:
> 
> In this `requests` checkout, the small pure-Python helper that lazily yields fixed-size chunks of a string (used internally to stream request and response bodies) currently silently treats `slice_length=0` and any negative integer as "use the whole string". Tighten the helper so that:
> 
> - Calling it with `slice_length=0` or any negative integer now raises `ValueError` whose message contains the substring `slice_length`.
> - Calling it with `slice_length=None` continues to mean "the whole string": iterating with `None` over `'abc'` still yields exactly `['abc']`.
> - Existing positive-`slice_length` behavior is preserved: chunks of length 2 over `'abcdef'` yield `['ab', 'cd', 'ef']`; chunks of length 3 over `'abcdefg'` yield `['abc', 'def', 'g']`; an empty input string yields `[]`.
> 
> The helper is a top-level generator function under `src/requests/`; locate it by searching the codebase for the docstring `Iterate over slices` or for the parameter named `slice_length`.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `exec_assert` | function `iter_slices` in `src/requests/utils.py` satisfies all 6 behavioral assertions (regression + new-behavior) |
| 2 | `call_schema_valid` | all tool calls match opencode schemas |
| 3 | `no_tool_name_recursive` | grep tool is denied; agent must use bash rg or read for context lookup |

## Why this mutant

Tests whether the agent pivots to `bash rg` or pure `read` when the native grep tool is denied. Especially relevant for search-heavy tasks (localization).

## Comparison points (panel-time)

The parent (`#51` `edit_iter_slices_require_positive`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
