# v1 #72 edit_peek_filelike_length_byteslike_fastpath

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='early-return-on-byteslike', scope_kind='single-file', answer_shape='value-equality', unique_trait='fast-path-len-on-bytes-bytearray-keep-fileno-and-seek-paths'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `peek_filelike_length` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `httpx` checkout, the small private helper that returns the byte length of a stream-like object (using `os.fstat`, then a `tell`/`seek` fallback) returns `None` when handed raw `bytes` or `bytearray` content -- because neither protocol is implemented on the bytes type and both `try`/`except` blocks fail. Add a fast path so that:
> 
> - Calling the helper with a `bytes` value returns `len(value)`. For example, calling it with `b'hello'` returns `5`, and calling it with `b''` returns `0`.
> - The same fast path applies to `bytearray`: calling the helper with `bytearray(b'world')` returns `5`.
> - Existing behaviour on every other input is preserved exactly: an `io.BytesIO` with content like `BytesIO(b'hello world')` still returns `11`; an empty `BytesIO(b'')` still returns `0`; an object that supports neither `.fileno()` nor `.tell()`/`.seek()` (e.g. a bare `object()`) still returns `None`.
> 
> The minimal change is a single guard at the very top of the function body that runs before either `try` block. Do NOT modify the existing `os.fstat` path, the `seek`/`tell` fallback, or the final `return length` line. The helper lives under the small networking helpers in the `httpx` package; locate it by searching for `os.fstat`, `os.SEEK_END`, or the documented file-length-peeking routine.

## Ground truth (reference edit)

`httpx/_utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def peek_filelike_length(stream: typing.Any) -> int | None:
    """
    Given a file-like stream object, return its length in number of bytes
    without reading it into memory.
    """
    try:
        # Is it an actual file?
        fd = stream.fileno()
        # Yup, seems to be an actual file.
        length = os.fstat(fd).st_size
    except (AttributeError, OSError):
        # No... Maybe it's something that supports random access, like `io.BytesIO`?
        try:
            # Assuming so, go to end of stream to figure out its length,
            # then put it back in place.
            offset = stream.tell()
            length = stream.seek(0, os.SEEK_END)
            stream.seek(offset)
        except (AttributeError, OSError):
            # Not even that? Sorry, we're doomed...
            return None

    return length
```

```python
# newString
def peek_filelike_length(stream: typing.Any) -> int | None:
    """
    Given a file-like stream object, return its length in number of bytes
    without reading it into memory.
    """
    if isinstance(stream, (bytes, bytearray)):
        return len(stream)
    try:
        # Is it an actual file?
        fd = stream.fileno()
        # Yup, seems to be an actual file.
        length = os.fstat(fd).st_size
    except (AttributeError, OSError):
        # No... Maybe it's something that supports random access, like `io.BytesIO`?
        try:
            # Assuming so, go to end of stream to figure out its length,
            # then put it back in place.
            offset = stream.tell()
            length = stream.seek(0, os.SEEK_END)
            stream.seek(offset)
        except (AttributeError, OSError):
            # Not even that? Sorry, we're doomed...
            return None

    return length
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `peek_filelike_length(BytesIO(b'hello world')) == 11` |
| 2 | regression | over-edit | `peek_filelike_length(BytesIO(b'')) == 0` |
| 3 | regression | over-edit | `peek_filelike_length(object()) is None` |
| 4 | new_behavior | no-change | `peek_filelike_length(b'hello') == 5` |
| 5 | new_behavior | partial-edit | `peek_filelike_length(b'') == 0` |
| 6 | new_behavior | partial-edit | `peek_filelike_length(bytearray(b'world')) == 5` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def peek_filelike_length` -> `httpx/_utils.py`
- `peek_filelike` -> `httpx/_content.py`, `httpx/_multipart.py`, `httpx/_utils.py`
- `os.SEEK_END` -> `httpx/_utils.py`

- Union (D = 3): `httpx/_content.py`, `httpx/_multipart.py`, `httpx/_utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

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

1. `exec_assert` (`httpx/_utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `peek_filelike_length(BytesIO(b'hello world')) == 11` (kind: regression)
- **over-edit**: caught by `peek_filelike_length(BytesIO(b'')) == 0` (kind: regression)
- **over-edit**: caught by `peek_filelike_length(object()) is None` (kind: regression)
- **no-change**: caught by `peek_filelike_length(b'hello') == 5` (kind: new_behavior)
- **partial-edit**: caught by `peek_filelike_length(b'') == 0` (kind: new_behavior)
- **partial-edit**: caught by `peek_filelike_length(bytearray(b'world')) == 5` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so calling the helper with `b'hello'` still returns `None` (`no-change`).
- Handles `bytes` but forgets `bytearray`, so the bytearray case still returns `None` (`partial-edit`).
- Adds the fast path AFTER the existing `try`/`except` blocks so it never runs (the `fileno()` / `tell()` calls raise but reach a final `return length` for the unrelated `length` variable that was set earlier) (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
