# v1 #72 edit_peek_filelike_length_byteslike_fastpath

## Category

code_editing

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Prompt

> In this `httpx` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `httpx/`; find it by searching the repo for the behavior described.
> 
> > The target is the small private helper inside `httpx`'s utilities that takes a stream-like object and tries to determine its length without reading it -- first via `os.fstat` on the underlying file descriptor, then via a `tell()`/`seek(0, os.SEEK_END)`/`seek(offset)` round-trip, returning `None` if neither path works. Callers occasionally hand it raw `bytes`/`bytearray` content (which has neither `.fileno()` nor `.tell()`/`.seek()`); today both paths fall through and the helper returns `None`, even though `len(value)` would have given the correct answer instantly.
> 
> Behavior contract:
> 
> In this `httpx` checkout, the small private helper that returns the byte length of a stream-like object (using `os.fstat`, then a `tell`/`seek` fallback) returns `None` when handed raw `bytes` or `bytearray` content -- because neither protocol is implemented on the bytes type and both `try`/`except` blocks fail. Add a fast path so that:
> 
> - Calling the helper with a `bytes` value returns `len(value)`. For example, calling it with `b'hello'` returns `5`, and calling it with `b''` returns `0`.
> - The same fast path applies to `bytearray`: calling the helper with `bytearray(b'world')` returns `5`.
> - Existing behaviour on every other input is preserved exactly: an `io.BytesIO` with content like `BytesIO(b'hello world')` still returns `11`; an empty `BytesIO(b'')` still returns `0`; an object that supports neither `.fileno()` nor `.tell()`/`.seek()` (e.g. a bare `object()`) still returns `None`.
> 
> The minimal change is a single guard at the very top of the function body that runs before either `try` block. Do NOT modify the existing `os.fstat` path, the `seek`/`tell` fallback, or the final `return length` line. The helper lives under the small networking helpers in the `httpx` package; locate it by searching for `os.fstat`, `os.SEEK_END`, or the documented file-length-peeking routine.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so calling the helper with `b'hello'` still returns `None` (`no-change`).
- Handles `bytes` but forgets `bytearray`, so the bytearray case still returns `None` (`partial-edit`).
- Adds the fast path AFTER the existing `try`/`except` blocks so it never runs (the `fileno()` / `tell()` calls raise but reach a final `return length` for the unrelated `length` variable that was set earlier) (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
