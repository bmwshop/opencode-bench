# v1 #208 m_locate_exception_tokens_deny_glob_system

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #28 `locate_exception_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "glob": {"*": "deny"}
  }
}
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, four exception classes in `src/requests/exceptions.py` represent the most common request-level failure modes: `ConnectionError`, `HTTPError`, `InvalidURL`, and `TooManyRedirects`.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function defined anywhere under `src/requests/` (any nesting depth, including methods on classes, mixins, and nested closures) whose body contains a direct call resolving by name to any of those four classes (i.e. the class is instantiated / called, typically in `raise X(...)` positions). Both bare-name calls (`X(...)`) and attribute calls (`self.X(...)`, `obj.X(...)`) count. Lines that only import or re-export those names do not count.
> 
> **Nested defs.** A call site physically inside a nested `def` (closure, inner helper) counts toward the enclosing function too — the enclosing function lexically contains that call site. The nested function is *also* a separate entry in its own right. So if a helper `generate` defined inside `Response.iter_content` contains a matching call, both `Response.iter_content` and `Response.iter_content.generate` appear in the answer.
> 
> **Exclusion by name.** Any function whose own unqualified name equals one of the target names is excluded from the answer, regardless of the class or module it is defined on. The target names for this sample are the unqualified names listed above (e.g. `close`, not `Session.close`); a function literally named `close` on *any* class is therefore never in the answer, even if its body contains a matching attribute call like `adapter.close()`.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (3 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 8 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | glob tool denied on a localization parent; agent must pivot to bash find or read |
