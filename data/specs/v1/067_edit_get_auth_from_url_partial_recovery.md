# v1 #67 edit_get_auth_from_url_partial_recovery

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> Modify the function `get_auth_from_url` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the `get_auth_from_url` helper declared at module scope inside `requests`. It parses a URL via `urlparse` and returns a `(username, password)` tuple, percent-decoded. Today, when only the username is present (e.g. `http://user@host.example/path`), the existing code calls `unquote(parsed.password)` -- where `parsed.password` is `None` -- which raises `TypeError`; the broad `except (AttributeError, TypeError)` catches it and the function returns `('', '')`, throwing away the username it could have recovered.
> 
> Behavior contract:
> 
> Modify the function `get_auth_from_url` (declared at module scope inside `requests`) so that a URL with only a username is decoded partially rather than collapsed to the empty tuple:
> 
> - Calling `get_auth_from_url('http://user@host.example/path')` now returns `('user', '')`. Percent-decoding still applies to the present field, so `get_auth_from_url('http://us%40er@host.example/path')` returns `('us@er', '')` (the `%40` becomes `@`).
> - Existing behaviour on every other input is preserved exactly: `get_auth_from_url('http://user:pass@host.example/path')` returns `('user', 'pass')`; `get_auth_from_url('')` returns `('', '')`; `get_auth_from_url('http://host.example/path')` (no auth at all) returns `('', '')`; and percent-decoding on both fields still works -- `get_auth_from_url('https://us%40er:p%23ss@host.example/path')` returns `('us@er', 'p#ss')`.
> 
> The minimal change is to compute `username` and `password` separately, defaulting each to the empty string when the corresponding component on the parsed URL is `None` rather than passing `None` to `unquote` and relying on the broad `except` to swallow the `TypeError`. Keep the surrounding `try`/`except (AttributeError, TypeError)` block in place as the safety net for genuinely malformed URLs.
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

- Leaves the function unchanged, so `get_auth_from_url('http://user@host.example/path')` still returns `('', '')` and the username is silently lost (`no-change`).
- Recovers the username when the password is missing but also stops percent-decoding (e.g. uses `parsed.username` directly instead of `unquote(parsed.username)`), so `'us%40er'` no longer round-trips to `'us@er'` (`partial-edit`).
- Removes the broad `except (AttributeError, TypeError)` safety net entirely, so a genuinely malformed URL now propagates an exception instead of returning `('', '')` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
