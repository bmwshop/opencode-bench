# v1 #209 m_locate_header_parse_tokens_deny_bash_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #44 `locate_header_parse_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Mutation

- **kind**: `deny_bash_system`
- **mechanism**: `opencode.json `permission``

Delivered through opencode's runtime permission layer (`opencode.json` `permission` block). Denied tools are hard-blocked: the model cannot call them at all -- attempts will be rejected by opencode before reaching the tool dispatcher.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "bash": "deny"
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, four module-level parsers in `src/requests/utils.py` tokenize RFC-7230 HTTP header values: `parse_header_links` (the `Link:` header), `parse_list_header` / `parse_dict_header` (quoted comma-separated pairs), and `_parse_content_type_header` (the media type with parameters).
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function defined anywhere under `src/requests/` (any nesting depth, including methods on classes, mixins, and nested closures) whose body contains a direct call resolving by name to any of those four parsers. Both bare-name calls (`X(...)`) and attribute calls (`self.X(...)`, `obj.X(...)`) count. Lines that only import or re-export those names do not count.
> 
> **Nested defs.** A call site physically inside a nested `def` (closure, inner helper) counts toward the enclosing function too — the enclosing function lexically contains that call site. The nested function is *also* a separate entry in its own right. So if a helper `generate` defined inside `Response.iter_content` contains a matching call, both `Response.iter_content` and `Response.iter_content.generate` appear in the answer.
> 
> **Exclusion by name.** Any function whose own unqualified name equals one of the target names is excluded from the answer, regardless of the class or module it is defined on. The target names for this sample are the unqualified names listed above (e.g. `close`, not `Session.close`); a function literally named `close` on *any* class is therefore never in the answer, even if its body contains a matching attribute call like `adapter.close()`.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 3 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | bash denied on a localization parent; agent must use native grep/glob/read |

## Why this mutant

Tests whether the agent can solve the task using only native tools when shell access is hard-blocked. Different tasks have different bash dependence -- this measures it directly.

## Comparison points (panel-time)

The parent (`#44` `locate_header_parse_tokens`) runs without any restriction. At panel time, the **delta** `parent_pass_rate - mutant_pass_rate` per model is the opencode-attributable signal: it isolates how much the *restriction itself* (and how opencode plumbs it) affected the same task on the same parent.

## Notes

- Restriction-honored verifier (e.g. `no_tool_name_recursive`) is the marker that the denied tool was actually absent from the trace. If opencode silently allows a denied tool, that verifier fires and the mutant fails -- which is itself a useful signal about opencode's enforcement layer.
