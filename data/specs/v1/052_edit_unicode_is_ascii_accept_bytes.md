# v1 #52 edit_unicode_is_ascii_accept_bytes

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='extend-acceptance', scope_kind='single-file', answer_shape='value-equality', unique_trait='accept-bytes-and-bytearray'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `unicode_is_ascii` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/_internal_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the internal helper that decides whether a text value contains only ASCII characters currently asserts that its argument is a `str` and refuses anything else. Loosen the helper so that:
> 
> - Passing a `str` keeps the existing behaviour exactly: `'hello'` returns `True`, `''` returns `True`, and a string containing a non-ASCII codepoint such as `'héllo'` returns `False`.
> - Passing a `bytes` value returns `True` iff every byte is strictly less than `128` -- for example `b'hello'` returns `True`, `b''` returns `True`, and `b'h\xc3\xa9llo'` returns `False`.
> - Passing a `bytearray` value behaves identically to the equivalent `bytes`: e.g. `bytearray(b'ok')` returns `True`.
> - Any other input continues to fail the existing `isinstance` assertion (i.e. raise `AssertionError`); do NOT broaden acceptance further.
> 
> The helper lives in a small internal-utilities module shared across the `requests` package; locate it by searching the codebase for its docstring (which describes "only contains ASCII" characters) or for the parameter named `u_string`.

## Ground truth (reference edit)

`src/requests/_internal_utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def unicode_is_ascii(u_string):
    """Determine if unicode string only contains ASCII characters.

    :param str u_string: unicode string to check. Must be unicode
        and not Python 2 `str`.
    :rtype: bool
    """
    assert isinstance(u_string, str)
    try:
        u_string.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False
```

```python
# newString
def unicode_is_ascii(u_string):
    """Determine if unicode string only contains ASCII characters.

    :param str u_string: unicode string to check. Must be unicode
        and not Python 2 `str`.
    :rtype: bool
    """
    if isinstance(u_string, (bytes, bytearray)):
        return all(b < 128 for b in u_string)
    assert isinstance(u_string, str)
    try:
        u_string.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False
```


## Hidden truth table (graders only) (N = 7)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `unicode_is_ascii('hello') is True` |
| 2 | regression | over-edit | `unicode_is_ascii('héllo') is False` |
| 3 | regression | over-edit | `unicode_is_ascii('') is True` |
| 4 | new_behavior | no-change | `unicode_is_ascii(b'hello') is True` |
| 5 | new_behavior | partial-edit | `unicode_is_ascii(b'h\xc3\xa9llo') is False` |
| 6 | new_behavior | partial-edit | `unicode_is_ascii(b'') is True` |
| 7 | new_behavior | partial-edit | `unicode_is_ascii(bytearray(b'ok')) is True` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def unicode_is_ascii` -> `src/requests/_internal_utils.py`
- `only contains ASCII` -> `src/requests/_internal_utils.py`
- `encode\("ascii"\)` -> `src/requests/_internal_utils.py`, `src/requests/utils.py`

- Union (D = 2): `src/requests/_internal_utils.py`, `src/requests/utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

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

1. `exec_assert` (`src/requests/_internal_utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `unicode_is_ascii('hello') is True` (kind: regression)
- **over-edit**: caught by `unicode_is_ascii('héllo') is False` (kind: regression)
- **over-edit**: caught by `unicode_is_ascii('') is True` (kind: regression)
- **no-change**: caught by `unicode_is_ascii(b'hello') is True` (kind: new_behavior)
- **partial-edit**: caught by `unicode_is_ascii(b'h\xc3\xa9llo') is False` (kind: new_behavior)
- **partial-edit**: caught by `unicode_is_ascii(b'') is True` (kind: new_behavior)
- **partial-edit**: caught by `unicode_is_ascii(bytearray(b'ok')) is True` (kind: new_behavior)

## Fail modes

- Leaves the `assert isinstance(u_string, str)` guard in place, so bytes inputs still fail the assertion (`no-change`).
- Accepts bytes but also changes the str path (e.g. now returns `True` for non-ASCII str because of a wrong `all(...)` predicate), breaking regression asserts (`over-edit`).
- Handles `bytes` but forgets `bytearray`, or uses a wrong threshold like `b < 127` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
