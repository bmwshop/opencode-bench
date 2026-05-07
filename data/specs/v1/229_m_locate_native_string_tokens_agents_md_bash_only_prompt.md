# v1 #229 m_locate_native_string_tokens_agents_md_bash_only_prompt

## Category

tool_restriction

## Parent

This is a tool-restriction MUTANT of v1 #46 `locate_native_string_tokens` (`code_localization`). The mutant inherits the parent's prompt and underlying task verifier; only the workspace overlay (and a few extra opencode-side compliance checks) differ.

## Workspace overlay

The agent's per-run workspace is the parent's pinned repo copy with the following additional file(s) layered on top:

### `AGENTS.md`

```markdown
## Tool Restriction

You must only use the bash tool. Do not use read, edit, write, glob, grep, task, or any other tool. Use bash for searching (e.g. `bash rg`, `bash find`), reading (`bash cat`), and writing (`bash echo > file`).
```

## Prompt

The prompt is the parent's prompt verbatim (no addendum). The mutation is delivered through the workspace overlay above, not by changing what the model is asked to do.

> In this `requests` checkout, an internal utility in `src/requests/_internal_utils.py` converts any bytes-like or text input into the platform's native `str` type (always `str` on Python 3); it is invoked wherever the library normalizes unstable mixed-type inputs — auth encoding, cookie header construction, URL preparation, and session request preparation all depend on it.
> 
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
> 
> - the module-level utility in `src/requests/_internal_utils.py` that performs the native-string normalization, or
> - every function defined in `src/requests/_internal_utils.py`, `src/requests/auth.py`, `src/requests/cookies.py`, `src/requests/models.py`, or `src/requests/sessions.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that utility.
> 
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (4 checks)

| # | type | description |
|---|------|-------------|
| 1 | `file_regex_disk` | location.txt must list exactly the 8 gold `file::QualifiedName` entries, in lexicographic order, one per line |
| 2 | `call_schema_valid` | _(no description)_ |
| 3 | `no_tool_name_recursive` | AGENTS.md bash-only on a hard localization parent (parent diversity vs #214 easy) |
| 4 | `any_tool_name_recursive` | agent must use bash to search and write location.txt |
