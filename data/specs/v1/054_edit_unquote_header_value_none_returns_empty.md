# v1 #54 edit_unquote_header_value_none_returns_empty

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `unquote_header_value` (plus in-file callees: _(none)_)
- Target file: `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

```python
# oldString
def unquote_header_value(value, is_filename=False):
    r"""Unquotes a header value.  (Reversal of :func:`quote_header_value`).
    This does not use the real unquoting but what browsers are actually
    using for quoting.

    :param value: the header value to unquote.
    :rtype: str
    """
    if value and value[0] == value[-1] == '"':
```

```python
# newString
def unquote_header_value(value, is_filename=False):
    r"""Unquotes a header value.  (Reversal of :func:`quote_header_value`).
    This does not use the real unquoting but what browsers are actually
    using for quoting.

    :param value: the header value to unquote.
    :rtype: str
    """
    if value is None:
        return ""
    if value and value[0] == value[-1] == '"':
```

## Truth table (N = 6)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `unquote_header_value('"hello"') == 'hello'` |
| 2 | regression | over-edit | `unquote_header_value('hello') == 'hello'` |
| 3 | regression | over-edit | `unquote_header_value('') == ''` |
| 4 | regression | over-edit | `unquote_header_value('"hello world"') == 'hello world'` |
| 5 | new_behavior | no-change | `unquote_header_value(None) == ''` |
| 6 | new_behavior | partial-edit | `unquote_header_value(None, is_filename=True) == ''` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def unquote_header_value` -> `src/requests/utils.py`
- `unquote_header_value` -> `src/requests/utils.py`
- `header value|header_value` -> `src/requests/exceptions.py`, `src/requests/models.py`, `src/requests/utils.py`
- `unquote` -> `src/requests/compat.py`, `src/requests/utils.py`

- Union (D = 4): `src/requests/compat.py`, `src/requests/exceptions.py`, `src/requests/models.py`, `src/requests/utils.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`unquote_header_value`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `unquote_header_value` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the internal helper that reverses `quote_header_value`, stripping the surrounding double quotes and unescaping `\\` and `\"` inside them. It lives in the `requests` utilities module and is invoked while parsing HTTP list-style headers.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert unquote_header_value('"hello"') == 'hello'
>     assert unquote_header_value('hello') == 'hello'
>     assert unquote_header_value('') == ''
>     assert unquote_header_value('"hello world"') == 'hello world'
>     assert unquote_header_value(None) == ''
>     assert unquote_header_value(None, is_filename=True) == ''
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every regression assert; do not delete existing behavior.
> - Use the exact exception class names that appear in the assertions above (e.g. `ValueError`, `TypeError`) -- other classes will not satisfy the asserts.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` `src/requests/utils.py` - every entry in the truth table above evaluates True against the patched file (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `unquote_header_value('"hello"') == 'hello'` (kind: regression)
- **over-edit**: caught by `unquote_header_value('hello') == 'hello'` (kind: regression)
- **over-edit**: caught by `unquote_header_value('') == ''` (kind: regression)
- **over-edit**: caught by `unquote_header_value('"hello world"') == 'hello world'` (kind: regression)
- **no-change**: caught by `unquote_header_value(None) == ''` (kind: new_behavior)
- **partial-edit**: caught by `unquote_header_value(None, is_filename=True) == ''` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `None` input returns `None` rather than `""` (`no-change`).
- Adds a top-level `if not value: return ""`, which changes the behavior for `""` (still `""`) but also silently discards any falsy-but-non-None exotic inputs (`over-edit`).
- Handles `None` but only for the default `is_filename=False` path, leaving `unquote_header_value(None, is_filename=True)` still returning `None` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
