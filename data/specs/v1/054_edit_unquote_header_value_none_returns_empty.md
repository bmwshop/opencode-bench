# v1 #54 edit_unquote_header_value_none_returns_empty

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

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

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so `None` input returns `None` rather than `""` (`no-change`).
- Adds a top-level `if not value: return ""`, which changes the behavior for `""` (still `""`) but also silently discards any falsy-but-non-None exotic inputs (`over-edit`).
- Handles `None` but only for the default `is_filename=False` path, leaving `unquote_header_value(None, is_filename=True)` still returning `None` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
