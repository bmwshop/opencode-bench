# v1 #53 edit_to_native_string_reject_unknown_with_caller

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **hard**
- leak_function_name: **false**
- structural_signature: `template='cross-file-contract', scope_kind='multi-file', answer_shape='cross-file-pair', unique_trait='impl-rejects-types-caller-rejects-none'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `to_native_string` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/_internal_utils.py`, `src/requests/auth.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; an edit to only one file will not satisfy the hidden grader.
> 
> Lower-level helper (in a small internal-utilities module of the package):
> 
> - The helper today coerces a `str` or `bytes` value into the native `str` type by calling `string.decode(encoding)` blindly on anything that isn't already a `str`, which raises `AttributeError` for non-string inputs (e.g. an `int`).
> - When given a `str`, it must return that `str` unchanged.
> - When given `bytes` or `bytearray`, it must decode using the `encoding` keyword (default `'ascii'`) and return a `str` -- for example `b'hello'` returns `'hello'`, and `b'h\xc3\xa9'` decoded as `'utf-8'` returns the single-character accented form `'hé'`.
> - When given anything else (`int`, `None`, `list`, etc.), it must raise `TypeError` whose message contains the substring `str or bytes`.
> 
> Higher-level helper (in a sibling file in the same package -- the basic-authentication helper module):
> 
> - There is a top-level helper that builds an HTTP `Basic <token>` authorization header from a username and a password and returns a string of the form `'Basic <base64>'`.
> - For two regular string inputs, it must continue to behave exactly as before -- e.g. `('user', 'pw')` returns `'Basic dXNlcjpwdw=='`.
> - When given `None` for the username, it must now treat the missing username as the empty bytes value `b""` (rather than warning and converting to the literal string `'None'`); concretely `(None, 'pw')` now returns `'Basic OnB3'`.
> - When given `None` for the password, it must symmetrically treat the missing password as `b""`; concretely `(None, None)` now returns `'Basic Og=='`.
> - Any non-`None`, non-string input (e.g. an integer) must continue to fall through to the existing deprecation-warning + `str(...)` coercion path -- do NOT remove that path.
> 
> Locate the lower-level helper by searching the codebase for the phrase `native string type`; locate the caller file by searching for the existing top-level builder of HTTP `Basic` authentication strings.

## Ground truth (reference edit)

`src/requests/_internal_utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def to_native_string(string, encoding="ascii"):
    """Given a string object, regardless of type, returns a representation of
    that string in the native string type, encoding and decoding where
    necessary. This assumes ASCII unless told otherwise.
    """
    if isinstance(string, builtin_str):
        out = string
    else:
        out = string.decode(encoding)

    return out
```

```python
# newString
def to_native_string(string, encoding="ascii"):
    """Given a string object, regardless of type, returns a representation of
    that string in the native string type, encoding and decoding where
    necessary. This assumes ASCII unless told otherwise.
    """
    if isinstance(string, builtin_str):
        return string
    if isinstance(string, (bytes, bytearray)):
        return bytes(string).decode(encoding)
    raise TypeError(
        f"to_native_string expected str or bytes, got {type(string).__name__}"
    )
```

`src/requests/auth.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    if not isinstance(username, basestring):
        warnings.warn(
            "Non-string usernames will no longer be supported in Requests "
            f"3.0.0. Please convert the object you've passed in ({username!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.",
            category=DeprecationWarning,
        )
        username = str(username)

    if not isinstance(password, basestring):
        warnings.warn(
            "Non-string passwords will no longer be supported in Requests "
            f"3.0.0. Please convert the object you've passed in ({type(password)!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.",
            category=DeprecationWarning,
        )
        password = str(password)
```

```python
# newString
    if username is None:
        username = b""
    elif not isinstance(username, basestring):
        warnings.warn(
            "Non-string usernames will no longer be supported in Requests "
            f"3.0.0. Please convert the object you've passed in ({username!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.",
            category=DeprecationWarning,
        )
        username = str(username)

    if password is None:
        password = b""
    elif not isinstance(password, basestring):
        warnings.warn(
            "Non-string passwords will no longer be supported in Requests "
            f"3.0.0. Please convert the object you've passed in ({type(password)!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.",
            category=DeprecationWarning,
        )
        password = str(password)
```


## Hidden truth table (graders only) (N = 7)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `to_native_string('hello') == 'hello'` _(with setup)_ |
| 2 | regression | over-edit | `to_native_string(b'hello') == 'hello'` _(with setup)_ |
| 3 | regression | over-edit | `to_native_string(b'h\xc3\xa9', encoding='utf-8') == 'hé'` _(with setup)_ |
| 4 | new_behavior | no-change | `raised is not None and 'str or bytes' in str(raised)` _(with setup)_ |
| 5 | regression | over-edit | `_basic_auth_str('user', 'pw') == 'Basic dXNlcjpwdw=='` _(with setup)_ |
| 6 | new_behavior | partial-edit | `_basic_auth_str(None, 'pw') == 'Basic OnB3'` |
| 7 | new_behavior | partial-edit | `_basic_auth_str(None, None) == 'Basic Og=='` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def to_native_string` -> `src/requests/_internal_utils.py`
- `def _basic_auth_str` -> `src/requests/auth.py`
- `native string type` -> `src/requests/_internal_utils.py`

- Union (D = 2): `src/requests/_internal_utils.py`, `src/requests/auth.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> In this `requests` checkout, satisfy the cross-file behavior contract below. The change requires consistent edits in TWO related files inside `src/requests/`. Find the relevant files by searching the repo for the behavior described.
> 
> > The target spans two related files: a lower-level coercion helper that converts a `str` or `bytes` value into the native `str` type, and a higher-level helper in a sibling file that uses the lower-level coercion to assemble an HTTP `Basic <token>` authorization header.
> 
> Behavior contract:
> 
> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; an edit to only one file will not satisfy the hidden grader.
> 
> Lower-level helper (in a small internal-utilities module of the package):
> 
> - The helper today coerces a `str` or `bytes` value into the native `str` type by calling `string.decode(encoding)` blindly on anything that isn't already a `str`, which raises `AttributeError` for non-string inputs (e.g. an `int`).
> - When given a `str`, it must return that `str` unchanged.
> - When given `bytes` or `bytearray`, it must decode using the `encoding` keyword (default `'ascii'`) and return a `str` -- for example `b'hello'` returns `'hello'`, and `b'h\xc3\xa9'` decoded as `'utf-8'` returns the single-character accented form `'hé'`.
> - When given anything else (`int`, `None`, `list`, etc.), it must raise `TypeError` whose message contains the substring `str or bytes`.
> 
> Higher-level helper (in a sibling file in the same package -- the basic-authentication helper module):
> 
> - There is a top-level helper that builds an HTTP `Basic <token>` authorization header from a username and a password and returns a string of the form `'Basic <base64>'`.
> - For two regular string inputs, it must continue to behave exactly as before -- e.g. `('user', 'pw')` returns `'Basic dXNlcjpwdw=='`.
> - When given `None` for the username, it must now treat the missing username as the empty bytes value `b""` (rather than warning and converting to the literal string `'None'`); concretely `(None, 'pw')` now returns `'Basic OnB3'`.
> - When given `None` for the password, it must symmetrically treat the missing password as `b""`; concretely `(None, None)` now returns `'Basic Og=='`.
> - Any non-`None`, non-string input (e.g. an integer) must continue to fall through to the existing deprecation-warning + `str(...)` coercion path -- do NOT remove that path.
> 
> Locate the lower-level helper by searching the codebase for the phrase `native string type`; locate the caller file by searching for the existing top-level builder of HTTP `Basic` authentication strings.
> 
> Constraints:
> - Edit exactly TWO files inside `src/requests/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`TypeError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/_internal_utils.py`, `src/requests/auth.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `to_native_string('hello') == 'hello'` (kind: regression)
- **over-edit**: caught by `to_native_string(b'hello') == 'hello'` (kind: regression)
- **over-edit**: caught by `to_native_string(b'h\xc3\xa9', encoding='utf-8') == 'hé'` (kind: regression)
- **no-change**: caught by `raised is not None and 'str or bytes' in str(raised)` (kind: new_behavior)
- **over-edit**: caught by `_basic_auth_str('user', 'pw') == 'Basic dXNlcjpwdw=='` (kind: regression)
- **partial-edit**: caught by `_basic_auth_str(None, 'pw') == 'Basic OnB3'` (kind: new_behavior)
- **partial-edit**: caught by `_basic_auth_str(None, None) == 'Basic Og=='` (kind: new_behavior)

## Fail modes

- Edits only the lower-level helper (raises `TypeError` for non-str/bytes) but leaves the higher-level builder unchanged, so `(None, 'pw')` still returns the leaked `'Basic Tm9uZTpwdw=='` (`partial-edit`).
- Edits only the higher-level builder (treats `None` as empty bytes) but leaves the lower-level helper as-is, so non-string inputs still raise `AttributeError` instead of `TypeError` (`partial-edit`).
- Removes the deprecation-warning path from the higher-level builder entirely, so non-`None` non-string inputs no longer go through the existing `str(...)` coercion (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
