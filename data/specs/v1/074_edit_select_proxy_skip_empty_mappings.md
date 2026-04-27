# v1 #74 edit_select_proxy_skip_empty_mappings

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='skip-empty-proxy-mappings', scope_kind='single-file', answer_shape='value-equality', unique_trait='skip-falsy-values-in-proxy-fallback-chain-keep-key-priority'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `select_proxy` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the small private helper that walks a four-step proxy-key fallback chain (`scheme://host`, `scheme`, `all://host`, `all`) currently short-circuits on the first key that exists in the `proxies` mapping -- regardless of whether the value at that key is truthy. Callers commonly use a falsy mapping like `{'http': None}` or `{'http': ''}` to signal 'do not use a proxy for this scheme, fall through to the `all` default'; the helper instead returns the falsy value, defeating the fallback. Tighten the chain so that:
> 
> - A falsy value at an earlier key (e.g. `{'http': None, 'all': 'http://fallback:8080'}` for the URL `http://host.example/path`) now falls through to the next key in the chain. The helper returns `'http://fallback:8080'` (the value under `'all'`).
> - The same fallthrough applies when the falsy value is the empty string: `{'http': '', 'all': 'http://fallback:8080'}` returns `'http://fallback:8080'`.
> - Existing behaviour on every other input is preserved exactly: a direct hit like `{'http': 'http://p1:8080'}` returns `'http://p1:8080'`; the `all` fallback like `{'all': 'http://p2:8080'}` returns `'http://p2:8080'`; `proxies=None` returns `None`; an empty `{}` returns `None`; a non-matching scheme like `{'https': 'http://p3:8080'}` (URL is `http://...`) returns `None`; and the host-specific key still wins over the bare scheme -- `{'http://host.example': 'http://specific:8080', 'http': 'http://generic:8080'}` returns `'http://specific:8080'`.
> 
> The minimal change extends the existing `if proxy_key in proxies:` check inside the fallback loop to also require the mapped value be truthy. Do NOT modify the four-key construction, the loop ordering, the early-return path for `urlparts.hostname is None`, or the trailing `return proxy`. The helper lives among the small URL-handling utilities under `src/requests/`; locate it by searching for `all://` references or for proxy-related call sites in the adapters layer.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    proxies = proxies or {}
    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]
    proxy = None
    for proxy_key in proxy_keys:
        if proxy_key in proxies:
            proxy = proxies[proxy_key]
            break

    return proxy
```

```python
# newString
    proxies = proxies or {}
    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]
    proxy = None
    for proxy_key in proxy_keys:
        if proxy_key in proxies and proxies[proxy_key]:
            proxy = proxies[proxy_key]
            break

    return proxy
```


## Hidden truth table (graders only) (N = 8)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `select_proxy('http://host.example/path', {'http': 'http://p1:8080'}) == 'http://p1:8080'` |
| 2 | regression | over-edit | `select_proxy('http://host.example/path', {'all': 'http://p2:8080'}) == 'http://p2:8080'` |
| 3 | regression | over-edit | `select_proxy('http://host.example/path', None) is None` |
| 4 | regression | over-edit | `select_proxy('http://host.example/path', {}) is None` |
| 5 | regression | over-edit | `select_proxy('http://host.example/path', {'https': 'http://p3:8080'}) is None` |
| 6 | regression | over-edit | `select_proxy('http://host.example/path', {'http://host.example': 'http://specific:8080', 'http': 'http://generic:8080'}) == 'http://specific:8080'` |
| 7 | new_behavior | no-change | `select_proxy('http://host.example/path', {'http': None, 'all': 'http://fallback:8080'}) == 'http://fallback:8080'` |
| 8 | new_behavior | partial-edit | `select_proxy('http://host.example/path', {'http': '', 'all': 'http://fallback:8080'}) == 'http://fallback:8080'` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def select_proxy` -> `src/requests/utils.py`
- `select_proxy` -> `src/requests/adapters.py`, `src/requests/utils.py`
- `all://` -> `src/requests/utils.py`

- Union (D = 2): `src/requests/adapters.py`, `src/requests/utils.py`

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

1. `exec_assert` (`src/requests/utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `select_proxy('http://host.example/path', {'http': 'http://p1:8080'}) == 'http://p1:8080'` (kind: regression)
- **over-edit**: caught by `select_proxy('http://host.example/path', {'all': 'http://p2:8080'}) == 'http://p2:8080'` (kind: regression)
- **over-edit**: caught by `select_proxy('http://host.example/path', None) is None` (kind: regression)
- **over-edit**: caught by `select_proxy('http://host.example/path', {}) is None` (kind: regression)
- **over-edit**: caught by `select_proxy('http://host.example/path', {'https': 'http://p3:8080'}) is None` (kind: regression)
- **over-edit**: caught by `select_proxy('http://host.example/path', {'http://host.example': 'http://specific:8080', 'http': 'http://generic:8080'}) == 'http://specific:8080'` (kind: regression)
- **no-change**: caught by `select_proxy('http://host.example/path', {'http': None, 'all': 'http://fallback:8080'}) == 'http://fallback:8080'` (kind: new_behavior)
- **partial-edit**: caught by `select_proxy('http://host.example/path', {'http': '', 'all': 'http://fallback:8080'}) == 'http://fallback:8080'` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so a falsy mapping at an earlier key returns the falsy value instead of falling through (`no-change`).
- Adds a truthiness check on the value but ALSO tightens the key membership test (e.g. `proxy_key in proxies and proxies[proxy_key] is not None`), accidentally accepting empty-string values which the test cases say should also fall through (`partial-edit`).
- Reorders the fallback chain so that bare `scheme` is checked before `scheme://host`, breaking the regression that the host-specific key wins (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
