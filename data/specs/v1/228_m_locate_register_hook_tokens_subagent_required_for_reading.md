# v1 #228 m_locate_register_hook_tokens_subagent_required_for_reading

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #41 `locate_register_hook_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

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

All file reading and grepping must be delegated to a subagent via the `task` tool. The parent must not call read, grep, or glob directly; you may still call `write` on the parent (to produce location.txt). To inspect any file, dispatch a subagent via `task` (e.g. with `subagent_type="explore"`) and use the subagent's returned summary.
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, a mixin class in `src/requests/models.py` exposes a method that appends a user-callback to the request's hook registry; its own `register_hook`/`deregister_hook` pair, the `Request` subclass's constructor, and an `HTTPDigestAuth` init helper all rely on that single registration entry-point.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the mixin method in `src/requests/models.py` that appends a callback to the hook registry, or
> - every function defined in `src/requests/models.py` or `src/requests/auth.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that method.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 4 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name` | parent must not call read/grep/glob directly on a medium localization parent |
| 4 | `any_tool_name_recursive` | a subagent must actually read at least one file |
| 5 | `any_tool_name` | parent must dispatch at least one task subagent |

## Why this mutant

AGENTS.md instructs the parent to delegate file reading to a subagent via the `task` tool. Tests subagent dispatch + consumption-of-subagent-output behavior under explicit delegation requirements.

## Comparison points (panel-time)

The parent (`#41` `locate_register_hook_tokens`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
- This sample is part of the v1 parents x v0 mutations batch; see `/Users/drekesh/.cursor/plans/v1_parents_x_v0_mutations.plan.md` for the full design and the 20-mutant table.
