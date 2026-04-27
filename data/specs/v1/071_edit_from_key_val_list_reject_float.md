# v1 #71 edit_from_key_val_list_reject_float

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='extend-rejection-set', scope_kind='single-file', answer_shape='raises-with-substring', unique_trait='extend-isinstance-tuple-with-float-and-complex'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `from_key_val_list` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the small helper that converts a value into an `OrderedDict` of key/value pairs (or returns `None`, or raises `ValueError` for non-2-tuple-like inputs) currently lets `float` and `complex` arguments slip past its `isinstance(value, (str, bytes, bool, int))` rejection. Such inputs reach `OrderedDict(value)` and produce an opaque `TypeError: 'float' object is not iterable` instead of the helper's documented `ValueError("cannot encode objects that are not 2-tuples")`. Tighten the helper so that:
> 
> - A `float` argument like `3.14` now raises `ValueError` whose message contains the substring `2-tuples`.
> - A `complex` argument like `1+2j` raises the same `ValueError` (also contains `2-tuples`).
> - Existing behaviour on every other input is preserved exactly: a `None` argument still returns `None`; a `dict` like `{'a': 1}` still produces an `OrderedDict` whose items are `[('a', 1)]`; a list of 2-tuples like `[('a', 1), ('b', 2)]` still produces an `OrderedDict` whose items are `[('a', 1), ('b', 2)]`; and a string argument like `'hello'` still raises `ValueError` with the same `2-tuples` substring it always has.
> 
> The minimal change extends the existing `isinstance(value, (str, bytes, bool, int))` rejection tuple. Do NOT modify the `None`-check, the `ValueError` message, or the trailing `OrderedDict(value)` fallback. The helper lives among the other small key/value coercion helpers under `src/requests/`; locate it by searching for the docstring substring `2-tuples` or the sibling `to_key_val_list`.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    return OrderedDict(value)
```

```python
# newString
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int, float, complex)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    return OrderedDict(value)
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `from_key_val_list(None) is None` |
| 2 | regression | over-edit | `list(from_key_val_list({'a': 1}).items()) == [('a', 1)]` |
| 3 | regression | over-edit | `list(from_key_val_list([('a', 1), ('b', 2)]).items()) == [('a', 1), ('b', 2)]` |
| 4 | regression | over-edit | `raised is not None and '2-tuples' in str(raised)` _(with setup)_ |
| 5 | new_behavior | no-change | `raised is not None and '2-tuples' in str(raised)` _(with setup)_ |
| 6 | new_behavior | partial-edit | `raised is not None and '2-tuples' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def from_key_val_list` -> `src/requests/utils.py`
- `2-tuples` -> `src/requests/models.py`, `src/requests/utils.py`
- `to_key_val_list` -> `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`

- Union (D = 3): `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`

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
> > The target is the small helper that takes a Python value and either returns `None` (for `None` input), raises `ValueError` (for clearly-not-key-value-list inputs like `'hello'` or `123`), or returns an ordered dictionary built from the value (for dicts and lists of 2-tuples). Today, scalar numeric types `float` and `complex` slip past the type-rejection branch -- they are not in the existing `(str, bytes, bool, int)` `isinstance` tuple -- and instead reach `OrderedDict(value)` where they raise an opaque `TypeError: 'float' object is not iterable` from deep inside CPython.
> 
> Behavior contract:
> 
> In this `requests` checkout, the small helper that converts a value into an `OrderedDict` of key/value pairs (or returns `None`, or raises `ValueError` for non-2-tuple-like inputs) currently lets `float` and `complex` arguments slip past its `isinstance(value, (str, bytes, bool, int))` rejection. Such inputs reach `OrderedDict(value)` and produce an opaque `TypeError: 'float' object is not iterable` instead of the helper's documented `ValueError("cannot encode objects that are not 2-tuples")`. Tighten the helper so that:
> 
> - A `float` argument like `3.14` now raises `ValueError` whose message contains the substring `2-tuples`.
> - A `complex` argument like `1+2j` raises the same `ValueError` (also contains `2-tuples`).
> - Existing behaviour on every other input is preserved exactly: a `None` argument still returns `None`; a `dict` like `{'a': 1}` still produces an `OrderedDict` whose items are `[('a', 1)]`; a list of 2-tuples like `[('a', 1), ('b', 2)]` still produces an `OrderedDict` whose items are `[('a', 1), ('b', 2)]`; and a string argument like `'hello'` still raises `ValueError` with the same `2-tuples` substring it always has.
> 
> The minimal change extends the existing `isinstance(value, (str, bytes, bool, int))` rejection tuple. Do NOT modify the `None`-check, the `ValueError` message, or the trailing `OrderedDict(value)` fallback. The helper lives among the other small key/value coercion helpers under `src/requests/`; locate it by searching for the docstring substring `2-tuples` or the sibling `to_key_val_list`.
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

- **no-change**: caught by `from_key_val_list(None) is None` (kind: regression)
- **over-edit**: caught by `list(from_key_val_list({'a': 1}).items()) == [('a', 1)]` (kind: regression)
- **over-edit**: caught by `list(from_key_val_list([('a', 1), ('b', 2)]).items()) == [('a', 1), ('b', 2)]` (kind: regression)
- **over-edit**: caught by `raised is not None and '2-tuples' in str(raised)` (kind: regression)
- **no-change**: caught by `raised is not None and '2-tuples' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and '2-tuples' in str(raised)` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `from_key_val_list(3.14)` still raises `TypeError` from inside `OrderedDict` rather than the helper's documented `ValueError` (`no-change`).
- Adds `float` to the rejection tuple but forgets `complex`, so the complex-number case still produces the opaque `TypeError` (`partial-edit`).
- Replaces the existing `(str, bytes, bool, int)` tuple with a different filter (e.g. `(int, float, complex)`), accidentally dropping the `str`/`bytes` rejections so `from_key_val_list('hello')` no longer raises (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
