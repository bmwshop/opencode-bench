# v1 #55 edit_parse_header_links_skip_empty_url

## Category

code_editing

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `src/requests/`; find it by searching the repo for the behavior described.
> 
> > The target is the small helper that parses HTTP `Link:` header values into a list of `{'url': ..., <params>}` dictionaries (used by `Response.links`). It lives in the `requests` utilities module alongside the other RFC-2068 header parsers.
> 
> Behavior contract:
> 
> In this `requests` checkout, the helper that parses an HTTP `Link:` header value into a list of `{'url': ..., <params>}` dictionaries currently includes entries whose `'url'` field is the empty string -- for example, a malformed header fragment like `<>; rel=junk` produces an entry with `'url': ''` instead of being skipped entirely. Tighten the helper so that:
> 
> - Entries whose parsed `'url'` field is the empty string are skipped from the returned list. For example, parsing `<>; rel=empty` returns `[]`. Parsing `<http://a.example/x>; rel=front, <>; rel=junk, <http://a.example/y>; rel=back` returns exactly two entries: `{'url': 'http://a.example/x', 'rel': 'front'}` and `{'url': 'http://a.example/y', 'rel': 'back'}` (the `<>` fragment is silently dropped).
> - Existing behaviour on well-formed inputs is preserved exactly: `<http://a.example/x>; rel=next` parses to `[{'url': 'http://a.example/x', 'rel': 'next'}]`; an empty input string still returns `[]`; a multi-link header carrying typed parameters such as `type="image/jpeg"` still produces both entries with their `'rel'` and `'type'` keys intact -- e.g. parsing the two-link form yields a list whose first dict is `{'url': 'http://a.example/x', 'rel': 'front', 'type': 'image/jpeg'}` and whose second is `{'url': 'http://a.example/y', 'rel': 'back', 'type': 'image/jpeg'}`.
> 
> The helper lives in the `requests` utilities module alongside the other RFC-2068 header parsers; locate it by searching for the docstring example mentioning `front.jpeg`.
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

- Leaves the function unchanged, so empty-URL entries continue to appear in the returned list (`no-change`).
- Filters too aggressively (e.g. drops entries when any single param value is empty, not just `url`), breaking the multi-link regression case (`over-edit`).
- Filters at the wrong stage (e.g. drops the entire iteration when one entry has empty `url`, instead of just skipping that one entry), so well-formed neighbouring entries are also lost (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
