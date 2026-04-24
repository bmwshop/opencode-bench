# v1 #53 edit_to_native_string_reject_unknown

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `to_native_string` (plus in-file callees: _(none)_)
- Target file: `src/requests/_internal_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/_internal_utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

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

## Truth table (N = 6)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `to_native_string('hello') == 'hello'` _(with setup)_ |
| 2 | regression | over-edit | `to_native_string(b'hello') == 'hello'` _(with setup)_ |
| 3 | regression | over-edit | `to_native_string(b'h\xc3\xa9', encoding='utf-8') == 'hé'` _(with setup)_ |
| 4 | new_behavior | no-change | `raised is not None and 'str or bytes' in str(raised)` _(with setup)_ |
| 5 | new_behavior | partial-edit | `raised is not None and 'str or bytes' in str(raised)` _(with setup)_ |
| 6 | new_behavior | partial-edit | `raised is not None and 'str or bytes' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def to_native_string` -> `src/requests/_internal_utils.py`
- `native string` -> `src/requests/_internal_utils.py`
- `builtin_str` -> `src/requests/_internal_utils.py`, `src/requests/compat.py`, `src/requests/models.py`

- Union (D = 3): `src/requests/_internal_utils.py`, `src/requests/compat.py`, `src/requests/models.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`to_native_string`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `to_native_string` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the internal helper that coerces a str or bytes value into the native `str` type. It lives in a small internal-utilities module shared across the requests package. The module already binds `builtin_str` to `str` via its imports.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     # setup: builtin_str = str
>     assert to_native_string('hello') == 'hello'
>     # setup: builtin_str = str
>     assert to_native_string(b'hello') == 'hello'
>     # setup: builtin_str = str
>     assert to_native_string(b'h\xc3\xa9', encoding='utf-8') == 'hé'
>     # setup: builtin_str = str ; raised = None ; try: ; to_native_string(42) ; except TypeError as e: ; raised = e
>     assert raised is not None and 'str or bytes' in str(raised)
>     # setup: builtin_str = str ; raised = None ; try: ; to_native_string(None) ; except TypeError as e: ; raised = e
>     assert raised is not None and 'str or bytes' in str(raised)
>     # setup: builtin_str = str ; raised = None ; try: ; to_native_string([1, 2, 3]) ; except TypeError as e: ; raised = e
>     assert raised is not None and 'str or bytes' in str(raised)
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every regression assert; do not delete existing behavior.
> - Use the exact exception class names that appear in the assertions above (e.g. `ValueError`, `TypeError`) -- other classes will not satisfy the asserts.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` `src/requests/_internal_utils.py` - every entry in the truth table above evaluates True against the patched file (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `to_native_string('hello') == 'hello'` (kind: regression)
- **over-edit**: caught by `to_native_string(b'hello') == 'hello'` (kind: regression)
- **over-edit**: caught by `to_native_string(b'h\xc3\xa9', encoding='utf-8') == 'hé'` (kind: regression)
- **no-change**: caught by `raised is not None and 'str or bytes' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and 'str or bytes' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and 'str or bytes' in str(raised)` (kind: new_behavior)

## Fail modes

- Leaves the `else: out = string.decode(encoding)` path, so non-str/bytes inputs raise `AttributeError` instead of `TypeError` (`no-change`).
- Raises `TypeError` for bytes as well, breaking the `b'hello'` regression case (`over-edit`).
- Raises `TypeError` but omits the `str or bytes` substring, or uses a `ValueError` instead (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
