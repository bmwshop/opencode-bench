# v1 #71 edit_from_key_val_list_reject_float

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

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

1. `exec_assert` (`src/requests/utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so `from_key_val_list(3.14)` still raises `TypeError` from inside `OrderedDict` rather than the helper's documented `ValueError` (`no-change`).
- Adds `float` to the rejection tuple but forgets `complex`, so the complex-number case still produces the opaque `TypeError` (`partial-edit`).
- Replaces the existing `(str, bytes, bool, int)` tuple with a different filter (e.g. `(int, float, complex)`), accidentally dropping the `str`/`bytes` rejections so `from_key_val_list('hello')` no longer raises (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
