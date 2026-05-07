# v1 #217 m_locate_header_parse_tokens_subagent_required_for_reading

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #44 `locate_header_parse_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `AGENTS.md`

```markdown
## Tool Restriction

All file reading and grepping must be delegated to a subagent via the `task` tool. The parent must not call read, grep, or glob directly; you may still call `write` on the parent (to produce location.txt). To inspect any file, dispatch a subagent via `task` (e.g. with `subagent_type="explore"`) and use the subagent's returned summary.
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

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 3 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name` | parent must not call read/grep/glob directly on a localization parent |
| 4 | `any_tool_name_recursive` | a subagent must actually read at least one file |
| 5 | `any_tool_name` | parent must dispatch at least one task subagent |
