# v1 #219 m_iter_slices_persona_main_bash_only

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #51 `edit_iter_slices_require_positive` (`code_editing`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `persona_main_bash_only`
- **source pattern**: borrowed from v0 #2 (`agents_md`)
- **mechanism**: `.opencode/agents/main.md`

Delivered through opencode's custom main agent persona file (`.opencode/agents/main.md`, modeled on v0 #2 `custom_main_agent`). The persona's prompt instructs the model on tool-use policy. This is the *third* delivery mechanism for instruction-based restrictions -- a useful comparison point against the AGENTS.md-based variant of the same restriction on the same parent.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `.opencode/agents/bash_only_editor.md`

```markdown
---
description: Strict bash-only editor persona for tool-restriction probes.
mode: primary
---

You are a strict bash-only editor. Your tool-use policy is:

- You may ONLY use the `bash` tool.
- You must NOT use the `read`, `edit`, `write`, `glob`, `grep`, or `task` tools.
- All file inspection, search, and modification must happen via shell commands run through `bash` (e.g. `python -c '...'`, `sed`, `cat`, `rg`, `find`).

This policy applies for the entire session. Follow it strictly.
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

## Pass criteria (4 checks)

| # | type | description |
|---|------|-------------|
| 1 | `exec_assert` | function `iter_slices` in `src/requests/utils.py` satisfies all 6 behavioral assertions (regression + new-behavior) |
| 2 | `call_schema_valid` | all tool calls match opencode schemas |
| 3 | `no_tool_name_recursive` | custom_main_agent persona forbids non-bash tools; same restriction as #212 via different mechanism |
| 4 | `any_tool_name_recursive` | agent must use bash to apply the edit |

## Why this mutant

Same restriction as the AGENTS.md-based bash-only mutant on the same parent, delivered through the custom main agent persona file. Comparison point for opencode's two instruction-delivery layers: does the persona-file path plumb the directive equally well as AGENTS.md?

## Comparison points (panel-time)

The parent (`#51` `edit_iter_slices_require_positive`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
