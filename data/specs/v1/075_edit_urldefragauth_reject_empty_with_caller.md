# v1 #75 edit_urldefragauth_reject_empty_with_caller

## Category

code_editing

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, satisfy the cross-file behavior contract below. The change requires consistent edits in TWO related files inside `src/requests/`. Find the relevant files by searching the repo for the behavior described.
> 
> > The target spans two related files inside `src/requests/`. The lower-level helper is a small URL-cleaning utility that strips both the URL fragment and the userinfo portion of the authority. The higher-level caller is the HTTP transport adapter that already houses `BaseAdapter`, `HTTPAdapter`, and the proxy-handling logic; it currently calls the lower-level helper directly without guarding against missing/empty URLs.
> 
> Behavior contract:
> 
> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level helper (in the small URL-cleaning utility module that already houses `parse_dict_header`, `parse_list_header`, and `select_proxy`):
> 
> - Today, the helper accepts any URL string -- including the empty string `''` -- and silently returns a stripped value. Empty input passes through `urlparse('')` and produces `''` as the final result, which is misleading because there is nothing to clean.
> - Tighten the helper so it raises `ValueError` with the message text `received empty url` (case-sensitive substring) when called on a falsy input (the empty string `''`). All other inputs continue to behave exactly as before.
> - All existing behaviour is preserved exactly: `'http://user:pass@example.com/path#frag'` still becomes `'http://example.com/path'`; `'http://example.com:8080/path'` still becomes `'http://example.com:8080/path'`; `'https://x@y.com/p?q=1#z'` still becomes `'https://y.com/p?q=1'`. Only the empty-string input changes behaviour (now raises).
> 
> Higher-level helper (in the sibling HTTP transport adapter module that already houses `BaseAdapter`, `HTTPAdapter`, and the existing top-level helper `_urllib3_request_context`):
> 
> - Add a NEW top-level helper named `_safe_urldefragauth(url)` that defends against missing or non-string `url` arguments before delegating to the lower-level helper. It must:
>   - Return `''` (the empty string) when `url` is `None`.
>   - Return `''` when `url` is not a string (e.g. a list, dict, or any other non-string value).
>   - Return `''` when `url` is a string that becomes empty after `str.strip()` (so whitespace-only strings short-circuit, never reaching the lower-level helper).
>   - Otherwise call the lower-level helper on the stripped string and return its result.
> - For example: `_safe_urldefragauth(None)` returns `''`; `_safe_urldefragauth('   ')` returns `''`; `_safe_urldefragauth(['not', 'a', 'string'])` returns `''`; `_safe_urldefragauth('http://user:pass@example.com/p#f')` returns `'http://example.com/p'`.
> 
> Locate the lower-level helper by searching the codebase for the docstring `remove the fragment` or for the trailing `.rsplit("@", 1)[-1]` line that strips the userinfo. Locate the sibling caller file by searching for `is_proxied_http_request` (a flag computed inside the adapter that already calls the lower-level helper).
> 
> Constraints:
> - Edit exactly TWO files inside `src/requests/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`, `src/requests/adapters.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Edits only the lower-level helper to raise on empty input but never adds the new sibling helper, so the new-behavior asserts on `_safe_urldefragauth` fail (`partial-edit`).
- Adds the sibling helper but doesn't tighten the lower-level helper, so calling the lower-level helper directly with `''` still returns `''` instead of raising (`partial-edit`).
- Tightens the lower-level helper to also reject `None` with a different exception class, breaking call sites that previously relied on `TypeError` from `urlparse(None)` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
