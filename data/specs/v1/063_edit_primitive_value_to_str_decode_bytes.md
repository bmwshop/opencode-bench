# v1 #63 edit_primitive_value_to_str_decode_bytes

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Prompt

> Modify the function `primitive_value_to_str` inside the `httpx` package so that the behavior contract below holds:
> 
> > The target is the small `primitive_value_to_str` coercion helper declared at module scope inside `httpx`. It currently maps `True` -> `'true'`, `False` -> `'false'`, `None` -> `''`, and falls back to `str(value)` for everything else; that fallback turns `bytes` values into ugly `"b'hello'"`-style repr strings instead of decoded text.
> 
> Behavior contract:
> 
> Modify the function `primitive_value_to_str` (declared at module scope inside `httpx`) so that it decodes `bytes` and `bytearray` values into UTF-8 text rather than falling through to `str(value)`:
> 
> - Calling `primitive_value_to_str(b'hello')` now returns `'hello'`. Calling `primitive_value_to_str(b'')` returns `''`. The decoding uses UTF-8.
> - Existing behaviour on the other primitives is preserved exactly: `primitive_value_to_str(True)` returns `'true'`, `primitive_value_to_str(False)` returns `'false'`, `primitive_value_to_str(None)` returns `''`, `primitive_value_to_str(123)` returns `'123'`, and `primitive_value_to_str('hello')` returns `'hello'`.
> 
> The minimal change is a single new branch inserted before the trailing `return str(value)` fallback. Do NOT modify the existing True/False/None branches.
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

- Leaves the function unchanged, so `primitive_value_to_str(b'hello')` still returns the ugly Python-repr form `"b'hello'"` (`no-change`).
- Decodes the bytes but uses the wrong codec (e.g. `latin-1`) so non-ASCII bytes round-trip incorrectly even though the simple `b'hello'` case happens to work (`partial-edit`).
- Catches bytes via the `str(value)` branch by special-casing inside an existing branch (e.g. moves the check inside the `is None` branch) and accidentally also returns `''` for non-empty bytes (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
