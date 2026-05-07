# v1 #44 locate_header_parse_tokens

## Category

code_localization

## Contract

completion

## Surface

tools

## Repo

`requests` — psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, four module-level parsers in `src/requests/utils.py` tokenize RFC-7230 HTTP header values: `parse_header_links` (the `Link:` header), `parse_list_header` / `parse_dict_header` (quoted comma-separated pairs), and `_parse_content_type_header` (the media type with parameters).
>
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function defined anywhere under `src/requests/` (any nesting depth, including methods on classes, mixins, and nested closures) whose body contains a direct call resolving by name to any of those four parsers. Both bare-name calls (`X(...)`) and attribute calls (`self.X(...)`, `obj.X(...)`) count. Lines that only import or re-export those names do not count.
>
> **Nested defs.** A call site physically inside a nested `def` (closure, inner helper) counts toward the enclosing function too — the enclosing function lexically contains that call site. The nested function is *also* a separate entry in its own right. So if a helper `generate` defined inside `Response.iter_content` contains a matching call, both `Response.iter_content` and `Response.iter_content.generate` appear in the answer.
>
> **Exclusion by name.** Any function whose own unqualified name equals one of the target names is excluded from the answer, regardless of the class or module it is defined on. The target names for this sample are the unqualified names listed above (e.g. `close`, not `Session.close`); a function literally named `close` on *any* class is therefore never in the answer, even if its body contains a matching attribute call like `adapter.close()`.
>
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (2 checks)

1. `file_regex_disk` `location.txt` — anchored regex demanding the exact 3-line gold above, optional trailing newline. Any deviation (wrong function, wrong file, missing/added entry, wrong qualname style, wrong sort, extra content) fails.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**≥ 2 tool calls** in practice: at least one `grep`/`bash rg` (or equivalent) to locate the relevant functions with enough context to resolve enclosing class + nesting, plus one `write` of `location.txt`. Careful agents add `read` calls to confirm function boundaries but are not required to by the rubric.

## Known fail modes

- Wrong/missing entry (e.g. overlooks a mixin caller, picks the wrong anchor) — anchored regex fails.
- Class prefix dropped (e.g. `send` instead of `Session.send`) or added on a module-level function — regex fails.
- Nested closure missed (e.g. `Response.iter_content.generate` flattened to `generate` or to `iter_content.generate` without the outer class) — regex fails.
- Paths written without the `src/requests/` prefix, or with a leading `./` — regex fails.
- Entries out of lexicographic order — regex fails.
- Malformed `write` args (e.g. `path` instead of `filePath`) — `call_schema_valid` fails even if the content would have matched.

## Intentionally *not* checked

- Free-form explanation text — only `location.txt` is scored.
- Which tools the agent uses to explore (`read`, `grep`, `glob`, `bash rg`, etc.) — any mix that produces the exact gold passes.
- Whether the agent reasons about inheritance, lifecycle, or mixin resolution order — only the artifact matters.
