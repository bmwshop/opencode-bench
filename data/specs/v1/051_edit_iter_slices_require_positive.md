# v1 #51 edit_iter_slices_require_positive

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='tighten-guard', scope_kind='single-file', answer_shape='raises-with-substring', unique_trait='reject-zero-and-negative-keep-none'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `iter_slices` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the small pure-Python helper that lazily yields fixed-size chunks of a string (used internally to stream request and response bodies) currently silently treats `slice_length=0` and any negative integer as "use the whole string". Tighten the helper so that:
> 
> - Calling it with `slice_length=0` or any negative integer now raises `ValueError` whose message contains the substring `slice_length`.
> - Calling it with `slice_length=None` continues to mean "the whole string": iterating with `None` over `'abc'` still yields exactly `['abc']`.
> - Existing positive-`slice_length` behavior is preserved: chunks of length 2 over `'abcdef'` yield `['ab', 'cd', 'ef']`; chunks of length 3 over `'abcdefg'` yield `['abc', 'def', 'g']`; an empty input string yields `[]`.
> 
> The helper is a top-level generator function under `src/requests/`; locate it by searching the codebase for the docstring `Iterate over slices` or for the parameter named `slice_length`.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

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


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `list(iter_slices('abcdef', 2)) == ['ab', 'cd', 'ef']` |
| 2 | regression | over-edit | `list(iter_slices('', 3)) == []` |
| 3 | regression | over-edit | `list(iter_slices('abc', None)) == ['abc']` |
| 4 | regression | over-edit | `list(iter_slices('abcdefg', 3)) == ['abc', 'def', 'g']` |
| 5 | new_behavior | no-change | `raised is not None and 'slice_length' in str(raised)` _(with setup)_ |
| 6 | new_behavior | partial-edit | `raised is not None and 'slice_length' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def iter_slices` -> `src/requests/utils.py`
- `Iterate over slices` -> `src/requests/utils.py`
- `chunked` -> `src/requests/adapters.py`, `src/requests/exceptions.py`, `src/requests/models.py`

- Union (D = 4): `src/requests/adapters.py`, `src/requests/exceptions.py`, `src/requests/models.py`, `src/requests/utils.py`

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
> > The target is the small pure-Python helper that lazily yields fixed-size chunks of a string (used internally to stream request and response bodies in chunks). It is defined in the `requests` utilities module.
> 
> Behavior contract:
> 
> In this `requests` checkout, the small pure-Python helper that lazily yields fixed-size chunks of a string (used internally to stream request and response bodies) currently silently treats `slice_length=0` and any negative integer as "use the whole string". Tighten the helper so that:
> 
> - Calling it with `slice_length=0` or any negative integer now raises `ValueError` whose message contains the substring `slice_length`.
> - Calling it with `slice_length=None` continues to mean "the whole string": iterating with `None` over `'abc'` still yields exactly `['abc']`.
> - Existing positive-`slice_length` behavior is preserved: chunks of length 2 over `'abcdef'` yield `['ab', 'cd', 'ef']`; chunks of length 3 over `'abcdefg'` yield `['abc', 'def', 'g']`; an empty input string yields `[]`.
> 
> The helper is a top-level generator function under `src/requests/`; locate it by searching the codebase for the docstring `Iterate over slices` or for the parameter named `slice_length`.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

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

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
