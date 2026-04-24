# v1 #51 edit_iter_slices_require_positive

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `iter_slices` (plus in-file callees: _(none)_)
- Target file: `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

```python
# oldString
def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None or slice_length <= 0:
        slice_length = len(string)
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length
```

```python
# newString
def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None:
        slice_length = len(string)
    elif not isinstance(slice_length, int) or slice_length <= 0:
        raise ValueError("iter_slices: slice_length must be a positive int or None")
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length
```

## Truth table (N = 6)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `list(iter_slices('abcdef', 2)) == ['ab', 'cd', 'ef']` |
| 2 | regression | over-edit | `list(iter_slices('', 3)) == []` |
| 3 | regression | over-edit | `list(iter_slices('abc', None)) == ['abc']` |
| 4 | regression | over-edit | `list(iter_slices('abcdefg', 3)) == ['abc', 'def', 'g']` |
| 5 | new_behavior | no-change | `raised is not None and 'slice_length' in str(raised)` _(with setup)_ |
| 6 | new_behavior | partial-edit | `raised is not None and 'slice_length' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def iter_slices` -> `src/requests/utils.py`
- `iter_slices` -> `src/requests/models.py`, `src/requests/utils.py`
- `slice.*length|length.*slice` -> `src/requests/utils.py`
- `Iterate over slices` -> `src/requests/utils.py`

- Union (D = 2): `src/requests/models.py`, `src/requests/utils.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`iter_slices`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `iter_slices` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the small pure-Python helper that lazily yields fixed-size chunks of a string (used internally to stream request/response bodies). It is defined in the `requests` utilities module.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert list(iter_slices('abcdef', 2)) == ['ab', 'cd', 'ef']
>     assert list(iter_slices('', 3)) == []
>     assert list(iter_slices('abc', None)) == ['abc']
>     assert list(iter_slices('abcdefg', 3)) == ['abc', 'def', 'g']
>     # setup: raised = None ; try: ; list(iter_slices('abc', 0)) ; except ValueError as e: ; raised = e
>     assert raised is not None and 'slice_length' in str(raised)
>     # setup: raised = None ; try: ; list(iter_slices('abc', -1)) ; except ValueError as e: ; raised = e
>     assert raised is not None and 'slice_length' in str(raised)
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

- **no-change**: caught by `list(iter_slices('abcdef', 2)) == ['ab', 'cd', 'ef']` (kind: regression)
- **over-edit**: caught by `list(iter_slices('', 3)) == []` (kind: regression)
- **over-edit**: caught by `list(iter_slices('abc', None)) == ['abc']` (kind: regression)
- **over-edit**: caught by `list(iter_slices('abcdefg', 3)) == ['abc', 'def', 'g']` (kind: regression)
- **no-change**: caught by `raised is not None and 'slice_length' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and 'slice_length' in str(raised)` (kind: new_behavior)

## Fail modes

- Leaves the `slice_length <= 0` branch silently defaulting to the full string length (`no-change`).
- Raises on every non-positive value but also rejects `None`, breaking the 'None means whole string' regression case (`over-edit`).
- Raises `TypeError` or a bare `Exception` instead of `ValueError`, or omits the `slice_length` substring from the error message (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
