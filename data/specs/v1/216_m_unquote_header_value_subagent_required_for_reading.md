# v1 #216 m_unquote_header_value_subagent_required_for_reading

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #54 `edit_unquote_header_value_none_returns_empty` (`code_editing`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `agents_md_subagent_required`
- **source pattern**: borrowed from v0 #19 (`subagent`)
- **mechanism**: `AGENTS.md`

Delivered through the workspace's `AGENTS.md` instruction file (modeled on v0 #12-#14 / #19). The denied tools remain *visible* in the model's tool list -- the restriction is instruction-based, so the verifier `no_tool_name_recursive` tests adherence rather than runtime blocking.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `AGENTS.md`

```markdown
## Tool Restriction

All file reading and grepping must be delegated to a subagent via the `task` tool. The parent must not call read, grep, or glob directly; you may still call `edit` on the parent. To inspect any file, dispatch a subagent via `task` (e.g. with `subagent_type="explore"`) and use the subagent's returned summary.
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

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `exec_assert` | function `unquote_header_value` in `src/requests/utils.py` satisfies all 6 behavioral assertions (regression + new-behavior) |
| 2 | `call_schema_valid` | all tool calls match opencode schemas |
| 3 | `no_tool_name` | parent must not call read/grep/glob directly; all reading goes through a subagent |
| 4 | `any_tool_name_recursive` | a subagent must actually read at least one file (recursive sees subagent layer) |
| 5 | `any_tool_name` | parent must dispatch at least one task subagent |

## Why this mutant

AGENTS.md instructs the parent to delegate file reading to a subagent via the `task` tool. Tests subagent dispatch + consumption-of-subagent-output behavior under explicit delegation requirements.

## Comparison points (panel-time)

The parent (`#54` `edit_unquote_header_value_none_returns_empty`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
