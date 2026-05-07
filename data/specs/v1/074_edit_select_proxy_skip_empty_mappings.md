# v1 #74 edit_select_proxy_skip_empty_mappings

## Category

code_editing

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `src/requests/`; find it by searching the repo for the behavior described.
> 
> > The target is the small private helper inside `requests` that, given a URL and a `proxies` dict, walks a four-step fallback chain (`scheme://host`, `scheme`, `all://host`, `all`) to pick the first matching proxy URL. Today the helper short-circuits on the FIRST key that is in the dict regardless of value -- so a falsy mapping like `{'http': None}` or `{'http': ''}` (which is how callers signal 'no proxy for this scheme') traps the lookup at the first step and returns the falsy value instead of falling through to the more general `all` mapping.
> 
> Behavior contract:
> 
> In this `requests` checkout, the small private helper that walks a four-step proxy-key fallback chain (`scheme://host`, `scheme`, `all://host`, `all`) currently short-circuits on the first key that exists in the `proxies` mapping -- regardless of whether the value at that key is truthy. Callers commonly use a falsy mapping like `{'http': None}` or `{'http': ''}` to signal 'do not use a proxy for this scheme, fall through to the `all` default'; the helper instead returns the falsy value, defeating the fallback. Tighten the chain so that:
> 
> - A falsy value at an earlier key (e.g. `{'http': None, 'all': 'http://fallback:8080'}` for the URL `http://host.example/path`) now falls through to the next key in the chain. The helper returns `'http://fallback:8080'` (the value under `'all'`).
> - The same fallthrough applies when the falsy value is the empty string: `{'http': '', 'all': 'http://fallback:8080'}` returns `'http://fallback:8080'`.
> - Existing behaviour on every other input is preserved exactly: a direct hit like `{'http': 'http://p1:8080'}` returns `'http://p1:8080'`; the `all` fallback like `{'all': 'http://p2:8080'}` returns `'http://p2:8080'`; `proxies=None` returns `None`; an empty `{}` returns `None`; a non-matching scheme like `{'https': 'http://p3:8080'}` (URL is `http://...`) returns `None`; and the host-specific key still wins over the bare scheme -- `{'http://host.example': 'http://specific:8080', 'http': 'http://generic:8080'}` returns `'http://specific:8080'`.
> 
> The minimal change extends the existing `if proxy_key in proxies:` check inside the fallback loop to also require the mapped value be truthy. Do NOT modify the four-key construction, the loop ordering, the early-return path for `urlparts.hostname is None`, or the trailing `return proxy`. The helper lives among the small URL-handling utilities under `src/requests/`; locate it by searching for `all://` references or for proxy-related call sites in the adapters layer.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so a falsy mapping at an earlier key returns the falsy value instead of falling through (`no-change`).
- Adds a truthiness check on the value but ALSO tightens the key membership test (e.g. `proxy_key in proxies and proxies[proxy_key] is not None`), accidentally accepting empty-string values which the test cases say should also fall through (`partial-edit`).
- Reorders the fallback chain so that bare `scheme` is checked before `scheme://host`, breaking the regression that the host-specific key wins (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
