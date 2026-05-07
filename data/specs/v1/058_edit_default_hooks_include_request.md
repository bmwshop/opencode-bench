# v1 #58 edit_default_hooks_include_request

## Category

code_editing

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> Modify the function `default_hooks` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the tiny hooks module that declares the list of hook event names and the helper `default_hooks` that returns a default, empty hook registry. The file already defines a module-level list of supported hook names; the default hook registry is built as a dict comprehension over that list.
> 
> Behavior contract:
> 
> Modify the function `default_hooks` and its supporting module-level state (declared in the tiny hooks module of the `requests` package) so that the hook system supports a `'request'` event in addition to the existing `'response'` event:
> 
> - The module-level list of hook event names (currently exactly `['response']`) must become exactly `['response', 'request']`, in that order, with length `2`.
> - `default_hooks()` must continue to return a `dict` whose `'response'` key maps to `[]` (the empty list).
> - `default_hooks()` must additionally have a `'request'` key that maps to `[]`.
> - `len(default_hooks())` must equal exactly `2`.
> 
> The minimal change is to extend the module-level list and let the existing dict comprehension propagate the new key automatically. Do NOT hard-code the `'request'` key directly in the comprehension or append a non-empty default callback list.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/hooks.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the module unchanged, so `'request' not in default_hooks()` (`no-change`).
- Adds `'request'` to the registry but as a non-empty list (e.g. a default callback), breaking the `== []` assert (`over-edit`).
- Adds `'request'` only to the returned dict via a hardcoded key, without updating the module-level list of hook names, so the new-behavior assert on the list fails (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
