# v1 #76 edit_to_key_val_list_sort_with_caller_filter_none

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, satisfy the cross-file behavior contract below. The change requires consistent edits in TWO related files inside `src/requests/`. Find the relevant files by searching the repo for the behavior described.
> 
> > The target spans two related files inside `src/requests/`. The lower-level helper is a small utility that normalizes user-supplied parameter/header inputs (mappings, list-of-tuples, generators) into a uniform list-of-tuples representation. The higher-level caller is the session module that already houses `merge_setting`, `merge_hooks`, and the request-merging plumbing; it currently consumes whatever insertion-order list the lower-level helper returns and has no defensive filter for `None` values that callers use to signal 'remove this entry'.
> 
> Behavior contract:
> 
> In this `requests` checkout, satisfy a contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level helper (in the small utility module that already houses `parse_dict_header`, `parse_list_header`, `select_proxy`, and the error message `cannot encode objects that are not 2-tuples`):
> 
> - Today, when the helper receives a `Mapping` (e.g. a `dict`), it returns `list(value.items())`, which preserves dict insertion order. Two callers that pass equivalent dicts with different insertion orders therefore see different output orderings, and downstream merging is order-sensitive.
> - Tighten the Mapping branch so it returns the items SORTED by key (lexicographic on the key as-is, no `str()` coercion). Concretely: `{'b': 2, 'a': 1, 'c': 3}` must now return `[('a', 1), ('b', 2), ('c', 3)]`; `{'z': 26, 'a': 1}` must return `[('a', 1), ('z', 26)]`.
> - All other behaviour is preserved exactly: a `list` of pairs passes through unchanged (`[('x', 1), ('y', 2)]` still returns `[('x', 1), ('y', 2)]`); `None` still returns `None`; `'string'` still raises `ValueError` with the message containing `cannot encode objects`. Do NOT change the rejection set (str/bytes/bool/int still raise) and do NOT sort non-Mapping inputs.
> 
> Higher-level helper (in the sibling session module that already houses the existing top-level `merge_setting` and `merge_hooks` helpers):
> 
> - Add a NEW top-level helper named `_kv_pairs_for_request(value)` that normalizes `value` to a list of `(key, val)` tuples with any pair whose value is `None` dropped. It must:
>   - Return `None` (the literal None, NOT `[]`) when `value` itself is `None` (passthrough; mirrors the lower-level helper's None-passthrough).
>   - Otherwise call the lower-level helper on `value`, then return a list comprehension that keeps only the `(k, v)` pairs where `v is not None`.
>   - The filter must use `is not None` (not truthiness): a pair like `('z', 0)` must be KEPT (zero is a legitimate value, only `None` is dropped).
> - For example: `_kv_pairs_for_request({'a': 1, 'b': None, 'c': 3})` returns `[('a', 1), ('c', 3)]`; `_kv_pairs_for_request([('x', 1), ('y', None), ('z', 0)])` returns `[('x', 1), ('z', 0)]`; `_kv_pairs_for_request({})` returns `[]`; `_kv_pairs_for_request(None)` returns `None`.
> 
> Locate the lower-level helper by searching the codebase for the exact error string `cannot encode objects that are not 2-tuples`. Locate the sibling caller file by searching for the existing top-level `merge_setting` helper.
> 
> Constraints:
> - Edit exactly TWO files inside `src/requests/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`, `src/requests/sessions.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Edits only the lower-level helper (sorts Mapping items) but never adds the new sibling helper, so the new-behavior asserts on `_kv_pairs_for_request` fail (`partial-edit`).
- Adds the sibling helper with the right None-filter but leaves the lower-level helper untouched, so the sort-on-Mapping assertions fail (`partial-edit`).
- Adds the sibling helper using truthy filter `if v` instead of `if v is not None`, dropping the `('z', 0)` pair as well as the `None` pair (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
