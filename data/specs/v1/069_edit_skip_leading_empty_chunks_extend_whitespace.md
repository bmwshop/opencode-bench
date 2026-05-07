# v1 #69 edit_skip_leading_empty_chunks_extend_whitespace

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
> > The target is a small private helper inside `httpx`'s WSGI transport that drops leading empty byte chunks from an iterable of body fragments before they reach the response. It currently treats only the truly-empty chunk `b''` as 'leading skippable noise' -- whitespace-only chunks like `b' '` or `b'\t'` are forwarded as the first chunk, which prevents downstream consumers from inspecting the real first content fragment.
> 
> Behavior contract:
> 
> In this `httpx` checkout, the small private helper inside the WSGI transport module currently drops only strictly-empty (`b''`) leading byte chunks from a stream of body fragments. Real-world WSGI applications occasionally yield whitespace-only chunks (`b' '`, `b'\t'`, `b'\n  \t'`) as bookkeeping output before the first real fragment, and downstream consumers expect those to be skipped just like empty chunks are. Extend the leading-skip predicate so that:
> 
> - Leading whitespace-only `bytes`/`bytearray`/`str` chunks are also skipped. For example, `list(helper([b'  ', b'\t', b'foo', b'bar']))` returns `[b'foo', b'bar']`, and `list(helper([b'\n  \t', b'foo']))` returns `[b'foo']`.
> - Existing behaviour on truly-empty leading chunks is preserved exactly: `list(helper([b'', b'foo', b'bar']))` returns `[b'foo', b'bar']`. An empty input still returns `[]`.
> - The pass-through-after-first-non-empty contract is preserved: `list(helper([b'foo', b'  ', b'bar']))` returns `[b'foo', b'  ', b'bar']` (whitespace AFTER the first real chunk is forwarded unchanged); a single-element non-empty stream like `list(helper([b'foo']))` returns `[b'foo']`.
> - Non-`bytes`/`bytearray`/`str` chunks must continue to be evaluated by their truthiness only (the helper is generic over chunk types), so the whitespace check applies only when the chunk is a `bytes`, `bytearray`, or `str`.
> 
> The minimal change extends the existing single `if chunk:` predicate to also reject whitespace-only `bytes`/`bytearray`/`str` chunks. Do NOT modify the `itertools.chain([chunk], body)` pass-through or the `return []` fallback. The helper lives among the WSGI integration glue under `httpx`; locate it by searching for `WSGI` or `itertools.chain` in the codebase.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_transports/wsgi.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so `[b'  ', b'\t', b'foo']` still yields `[b'  ', b'\t', b'foo']` instead of `[b'foo']` (`no-change`).
- Adds the whitespace check but applies it to ALL chunks (not just leading), so `list(helper([b'foo', b'  ', b'bar']))` becomes `[b'foo', b'bar']` instead of `[b'foo', b'  ', b'bar']` (`over-edit`).
- Strips whitespace too aggressively (e.g. checks `chunk.isspace()` on bytes which is a method that exists but interprets the encoding loosely), passing for `b'\xc2\xa0'` (non-breaking space in UTF-8) when it shouldn't (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
