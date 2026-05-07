# v1 #52 edit_unicode_is_ascii_accept_bytes

## Category

code_editing

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `src/requests/`; find it by searching the repo for the behavior described.
> 
> > The target is the internal helper that tests whether a text value contains only ASCII characters. It lives in a small internal-utilities module shared across the requests package.
> 
> Behavior contract:
> 
> In this `requests` checkout, the internal helper that decides whether a text value contains only ASCII characters currently asserts that its argument is a `str` and refuses anything else. Loosen the helper so that:
> 
> - Passing a `str` keeps the existing behaviour exactly: `'hello'` returns `True`, `''` returns `True`, and a string containing a non-ASCII codepoint such as `'héllo'` returns `False`.
> - Passing a `bytes` value returns `True` iff every byte is strictly less than `128` -- for example `b'hello'` returns `True`, `b''` returns `True`, and `b'h\xc3\xa9llo'` returns `False`.
> - Passing a `bytearray` value behaves identically to the equivalent `bytes`: e.g. `bytearray(b'ok')` returns `True`.
> - Any other input continues to fail the existing `isinstance` assertion (i.e. raise `AssertionError`); do NOT broaden acceptance further.
> 
> The helper lives in a small internal-utilities module shared across the `requests` package; locate it by searching the codebase for its docstring (which describes "only contains ASCII" characters) or for the parameter named `u_string`.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/_internal_utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the `assert isinstance(u_string, str)` guard in place, so bytes inputs still fail the assertion (`no-change`).
- Accepts bytes but also changes the str path (e.g. now returns `True` for non-ASCII str because of a wrong `all(...)` predicate), breaking regression asserts (`over-edit`).
- Handles `bytes` but forgets `bytearray`, or uses a wrong threshold like `b < 127` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
