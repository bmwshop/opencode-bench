# v1 #51 edit_iter_slices_require_positive

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

1. `exec_assert` (`src/requests/utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the `slice_length <= 0` branch silently defaulting to the full string length (`no-change`).
- Raises on every non-positive value but also rejects `None`, breaking the 'None means whole string' regression case (`over-edit`).
- Raises `TypeError` or a bare `Exception` instead of `ValueError`, or omits the `slice_length` substring from the error message (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
