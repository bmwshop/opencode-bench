# v1 #59 edit_dispatch_hook_skip_none_with_caller

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
> > The target spans two related files: a low-level hook dispatcher in the tiny hooks module, plus a defensive wrapper that the agent must add to the session module that already houses `merge_hooks` and `merge_setting`.
> 
> Behavior contract:
> 
> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level dispatcher (in the tiny hooks module of the package):
> 
> - Today, the dispatcher runs every registered callback for an event against a piece of data, returning the last non-`None` callback result. If the callback list contains a `None` entry the dispatcher crashes (calling `None(...)` raises `TypeError: 'NoneType' object is not callable`).
> - Tighten the dispatcher so a `None` entry in the callback list is silently skipped. Concretely: with `hook_data=10` and the callback list `[lambda d: d + 1]`, the dispatcher must still return `11`; with the same data and the list `[None, lambda d: d + 1]`, the dispatcher must now return `11` (the `None` entry is skipped); with `[None]` it must return `10`.
> - All existing behaviour is preserved exactly: with no hooks the data is returned unchanged; with a hooks dict of `None` or `{}` the data is returned unchanged; a single-callable hook value (not wrapped in a list) is still invoked; chained hooks still propagate the last non-`None` callback result.
> 
> Higher-level helper (in the sibling session module that already contains the existing top-level `merge_hooks` and `merge_setting` helpers):
> 
> - Add a NEW top-level helper named `apply_response_hooks(hooks, response)` that defends against malformed `hooks` arguments before delegating to the lower-level dispatcher. It must:
>   - Return `response` unchanged when `hooks` is `None`.
>   - Return `response` unchanged when `hooks` is not a `dict` (e.g. a list or any other non-dict value).
>   - Return `response` unchanged when `hooks` is a dict that does not contain the key `'response'`.
>   - Otherwise delegate to the lower-level dispatcher with the event key `'response'` (and return its result).
> - For example: `apply_response_hooks(None, 'r')` returns `'r'`; `apply_response_hooks({}, 'r')` returns `'r'`; and `apply_response_hooks({'response': [None, lambda d: d.upper()]}, 'hi')` returns `'HI'`.
> 
> Locate the lower-level dispatcher by searching the codebase for the docstring `Dispatches a hook` or for the callback-iteration loop; locate the sibling caller file by searching for the existing top-level `merge_hooks` helper.
> 
> Constraints:
> - Edit exactly TWO files inside `src/requests/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/hooks.py`, `src/requests/sessions.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Edits only the lower-level dispatcher (skips `None` entries) but never adds the new sibling helper, so the new-behavior asserts on `apply_response_hooks` fail (`partial-edit`).
- Adds the sibling helper but doesn't touch the dispatcher, so a `None` entry in a callback list still crashes the dispatcher (`partial-edit`).
- Replaces the callback list with `[h for h in hooks if h]`, which also drops other falsy callbacks instead of just `None` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
