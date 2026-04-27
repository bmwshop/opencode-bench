# v1 #220 m_unquote_header_value_persona_main_subagent_required

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #54 `edit_unquote_header_value_none_returns_empty` (`code_editing`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `persona_main_subagent_required`
- **source pattern**: borrowed from v0 #2 (`agents_md`)
- **mechanism**: `.opencode/agents/main.md`

Delivered through opencode's custom main agent persona file (`.opencode/agents/main.md`, modeled on v0 #2 `custom_main_agent`). The persona's prompt instructs the model on tool-use policy. This is the *third* delivery mechanism for instruction-based restrictions -- a useful comparison point against the AGENTS.md-based variant of the same restriction on the same parent.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `.opencode/agents/subagent_first_editor.md`

```markdown
---
description: Delegation-first editor persona; reading goes through subagents.
mode: primary
---

You are a delegation-first editor. Your tool-use policy is:

- All file reading and grepping must be delegated to a subagent via the `task` tool.
- You must NOT call `read`, `grep`, or `glob` directly.
- You MAY call `edit` to apply the patch.
- For every file you need to inspect, dispatch a subagent via `task` (e.g. with `subagent_type="explore"`) and rely on the subagent's returned summary.

This policy applies for the entire session. Same restriction as the AGENTS.md-based variant on #216, delivered through this persona file.
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
| 3 | `no_tool_name` | persona file forbids parent reading; same restriction as #216 via different mechanism |
| 4 | `any_tool_name_recursive` | a subagent must actually read at least one file |
| 5 | `any_tool_name` | parent must dispatch at least one task subagent |

## Why this mutant

Same restriction as the AGENTS.md-based subagent-required mutant on the same parent, delivered through the persona file. Comparison point for opencode's two instruction-delivery layers.

## Comparison points (panel-time)

The parent (`#54` `edit_unquote_header_value_none_returns_empty`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
