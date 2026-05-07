# v1 #70 edit_normalize_header_value_reject_crlf

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Prompt

> In this `httpx` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `httpx/`; find it by searching the repo for the behavior described.
> 
> > The target is the small private helper that coerces a `str` or `bytes` HTTP header value into bytes. It currently passes `bytes` through, encodes `str` with the supplied encoding (default `'ascii'`), and raises `TypeError` for everything else. Header values containing carriage-return (`\r`) or line-feed (`\n`) bytes leak past the helper unchanged -- a classic header-injection vector that lets a hostile caller smuggle additional response headers.
> 
> Behavior contract:
> 
> In this `httpx` checkout, the small private helper that coerces a header value (currently typed as `str | bytes`) into a strict byte string forwards strings containing carriage-return (`\r`) or line-feed (`\n`) characters straight through to the byte encoder. That allows a hostile caller to smuggle additional headers via a payload like `'session=xyz\r\nX-Evil: yes'`. Tighten the helper so that:
> 
> - A `str` value containing `\r` or `\n` now raises `ValueError` whose message contains either `CR` or `LF`. For example, calling the helper with `'value\r\nX-Evil: yes'` raises `ValueError`; calling it with `'value\nX-Evil: yes'` (LF only) also raises `ValueError`.
> - Existing behaviour on safe inputs is preserved exactly: a clean `str` like `'hello'` still encodes to `b'hello'`; a `bytes` value like `b'hello'` is still passed through; a clean `str` like `'worth-keeping'` still encodes to `b'worth-keeping'`; and the existing `TypeError` for non-`str`/non-`bytes` values (e.g. `123`) is still raised unchanged.
> 
> The minimal change adds a single guard *after* the existing `str`/`bytes` type checks but *before* the `value.encode(...)` call. Do NOT modify the existing type-check logic, the `TypeError` message, or the encoding fallback (`encoding or "ascii"`). Note: this guard intentionally does NOT inspect `bytes` values for embedded `b'\r'` / `b'\n'`; tightening the bytes path is left as a separate concern.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`TypeError`, `ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_models.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so a CRLF-containing string is encoded straight to bytes and the injection vector is preserved (`no-change`).
- Adds the CRLF check but ALSO inspects `bytes` values for embedded `b'\r'`/`b'\n'`, breaking the regression that `bytes` values pass through unchanged (`over-edit`).
- Raises a different exception class (e.g. `TypeError` rather than `ValueError`), so the existing `try: ... except TypeError` callers swallow the new behaviour and the CRLF still leaks (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
