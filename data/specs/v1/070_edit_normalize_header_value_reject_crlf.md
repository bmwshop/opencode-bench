# v1 #70 edit_normalize_header_value_reject_crlf

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='tighten-injection-prevention', scope_kind='single-file', answer_shape='raises-with-substring', unique_trait='reject-crlf-in-str-keep-bytes-passthrough'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `_normalize_header_value` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_models.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `httpx` checkout, the small private helper that coerces a header value (currently typed as `str | bytes`) into a strict byte string forwards strings containing carriage-return (`\r`) or line-feed (`\n`) characters straight through to the byte encoder. That allows a hostile caller to smuggle additional headers via a payload like `'session=xyz\r\nX-Evil: yes'`. Tighten the helper so that:
> 
> - A `str` value containing `\r` or `\n` now raises `ValueError` whose message contains either `CR` or `LF`. For example, calling the helper with `'value\r\nX-Evil: yes'` raises `ValueError`; calling it with `'value\nX-Evil: yes'` (LF only) also raises `ValueError`.
> - Existing behaviour on safe inputs is preserved exactly: a clean `str` like `'hello'` still encodes to `b'hello'`; a `bytes` value like `b'hello'` is still passed through; a clean `str` like `'worth-keeping'` still encodes to `b'worth-keeping'`; and the existing `TypeError` for non-`str`/non-`bytes` values (e.g. `123`) is still raised unchanged.
> 
> The minimal change adds a single guard *after* the existing `str`/`bytes` type checks but *before* the `value.encode(...)` call. Do NOT modify the existing type-check logic, the `TypeError` message, or the encoding fallback (`encoding or "ascii"`). Note: this guard intentionally does NOT inspect `bytes` values for embedded `b'\r'` / `b'\n'`; tightening the bytes path is left as a separate concern.

## Ground truth (reference edit)

`httpx/_models.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def _normalize_header_value(value: str | bytes, encoding: str | None = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Header value must be str or bytes, not {type(value)}")
    return value.encode(encoding or "ascii")
```

```python
# newString
def _normalize_header_value(value: str | bytes, encoding: str | None = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Header value must be str or bytes, not {type(value)}")
    if "\r" in value or "\n" in value:
        raise ValueError(
            "_normalize_header_value: header value must not contain CR or LF"
        )
    return value.encode(encoding or "ascii")
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `_normalize_header_value('hello') == b'hello'` |
| 2 | regression | over-edit | `_normalize_header_value(b'hello') == b'hello'` |
| 3 | regression | over-edit | `_normalize_header_value('worth-keeping') == b'worth-keeping'` |
| 4 | regression | over-edit | `raised is not None` _(with setup)_ |
| 5 | new_behavior | no-change | `raised is not None and ('CR' in str(raised) or 'LF' in str(raised))` _(with setup)_ |
| 6 | new_behavior | partial-edit | `raised is not None and ('CR' in str(raised) or 'LF' in str(raised))` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def _normalize_header_value` -> `httpx/_models.py`
- `header_value` -> `httpx/_auth.py`, `httpx/_models.py`, `httpx/_multipart.py`, `httpx/_transports/wsgi.py`
- `Header value must` -> `httpx/_models.py`

- Union (D = 4): `httpx/_auth.py`, `httpx/_models.py`, `httpx/_multipart.py`, `httpx/_transports/wsgi.py`

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

1. `exec_assert` (`httpx/_models.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `_normalize_header_value('hello') == b'hello'` (kind: regression)
- **over-edit**: caught by `_normalize_header_value(b'hello') == b'hello'` (kind: regression)
- **over-edit**: caught by `_normalize_header_value('worth-keeping') == b'worth-keeping'` (kind: regression)
- **over-edit**: caught by `raised is not None` (kind: regression)
- **no-change**: caught by `raised is not None and ('CR' in str(raised) or 'LF' in str(raised))` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and ('CR' in str(raised) or 'LF' in str(raised))` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so a CRLF-containing string is encoded straight to bytes and the injection vector is preserved (`no-change`).
- Adds the CRLF check but ALSO inspects `bytes` values for embedded `b'\r'`/`b'\n'`, breaking the regression that `bytes` values pass through unchanged (`over-edit`).
- Raises a different exception class (e.g. `TypeError` rather than `ValueError`), so the existing `try: ... except TypeError` callers swallow the new behaviour and the CRLF still leaks (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
