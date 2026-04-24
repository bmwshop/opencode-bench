# v1 #52 edit_unicode_is_ascii_accept_bytes

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `unicode_is_ascii` (plus in-file callees: _(none)_)
- Target file: `src/requests/_internal_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/_internal_utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

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

## Truth table (N = 7)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

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

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def unicode_is_ascii` -> `src/requests/_internal_utils.py`
- `unicode_is_ascii` -> `src/requests/_internal_utils.py`, `src/requests/models.py`
- `ASCII|ascii` -> `src/requests/_internal_utils.py`, `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`
- `encode\(['\"]ascii` -> `src/requests/_internal_utils.py`, `src/requests/utils.py`

- Union (D = 4): `src/requests/_internal_utils.py`, `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`unicode_is_ascii`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `unicode_is_ascii` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the internal helper that tests whether a text value contains only ASCII characters. It lives in a small internal-utilities module shared across the requests package.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert unicode_is_ascii('hello') is True
>     assert unicode_is_ascii('héllo') is False
>     assert unicode_is_ascii('') is True
>     assert unicode_is_ascii(b'hello') is True
>     assert unicode_is_ascii(b'h\xc3\xa9llo') is False
>     assert unicode_is_ascii(b'') is True
>     assert unicode_is_ascii(bytearray(b'ok')) is True
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

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
