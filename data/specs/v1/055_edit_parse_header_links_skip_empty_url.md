# v1 #55 edit_parse_header_links_skip_empty_url

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='extend-comprehension', scope_kind='single-file', answer_shape='value-equality', unique_trait='filter-empty-url-entries-from-link-list'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `parse_header_links` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the helper that parses an HTTP `Link:` header value into a list of `{'url': ..., <params>}` dictionaries currently includes entries whose `'url'` field is the empty string -- for example, a malformed header fragment like `<>; rel=junk` produces an entry with `'url': ''` instead of being skipped entirely. Tighten the helper so that:
> 
> - Entries whose parsed `'url'` field is the empty string are skipped from the returned list. For example, parsing `<>; rel=empty` returns `[]`. Parsing `<http://a.example/x>; rel=front, <>; rel=junk, <http://a.example/y>; rel=back` returns exactly two entries: `{'url': 'http://a.example/x', 'rel': 'front'}` and `{'url': 'http://a.example/y', 'rel': 'back'}` (the `<>` fragment is silently dropped).
> - Existing behaviour on well-formed inputs is preserved exactly: `<http://a.example/x>; rel=next` parses to `[{'url': 'http://a.example/x', 'rel': 'next'}]`; an empty input string still returns `[]`; a multi-link header carrying typed parameters such as `type="image/jpeg"` still produces both entries with their `'rel'` and `'type'` keys intact -- e.g. parsing the two-link form yields a list whose first dict is `{'url': 'http://a.example/x', 'rel': 'front', 'type': 'image/jpeg'}` and whose second is `{'url': 'http://a.example/y', 'rel': 'back', 'type': 'image/jpeg'}`.
> 
> The helper lives in the `requests` utilities module alongside the other RFC-2068 header parsers; locate it by searching for the docstring example mentioning `front.jpeg`.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links
```

```python
# newString
    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        if link["url"]:
            links.append(link)

    return links
```


## Hidden truth table (graders only) (N = 5)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | over-edit | `parse_header_links('<http://a.example/x>; rel=next') == [{'url': 'http://a.example/x', 'rel': 'next'}]` |
| 2 | regression | no-change | `parse_header_links('') == []` |
| 3 | regression | over-edit | `parse_header_links('<http://a.example/x>; rel=front; type="image/jpeg", <http://a.example/y>; rel=back; type="image/jpeg"') == [{'url': 'http://a.example/x', 'rel': 'front', 'type': 'image/jpeg'}, {'url': 'http://a.example/y', 'rel': 'back', 'type': 'image/jpeg'}]` |
| 4 | new_behavior | no-change | `parse_header_links('<>; rel=empty') == []` |
| 5 | new_behavior | partial-edit | `parse_header_links('<http://a.example/x>; rel=front, <>; rel=junk, <http://a.example/y>; rel=back') == [{'url': 'http://a.example/x', 'rel': 'front'}, {'url': 'http://a.example/y', 'rel': 'back'}]` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def parse_header_links` -> `src/requests/utils.py`
- `header_links` -> `src/requests/models.py`, `src/requests/utils.py`
- `front.jpeg` -> `src/requests/utils.py`

- Union (D = 2): `src/requests/models.py`, `src/requests/utils.py`

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

1. `exec_assert` (`src/requests/utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **over-edit**: caught by `parse_header_links('<http://a.example/x>; rel=next') == [{'url': 'http://a.example/x', 'rel': 'next'}]` (kind: regression)
- **no-change**: caught by `parse_header_links('') == []` (kind: regression)
- **over-edit**: caught by `parse_header_links('<http://a.example/x>; rel=front; type="image/jpeg", <http://a.example/y>; rel=back; type="image/jpeg"') == [{'url': 'http://a.example/x', 'rel': 'front', 'type': 'image/jpeg'}, {'url': 'http://a.example/y', 'rel': 'back', 'type': 'image/jpeg'}]` (kind: regression)
- **no-change**: caught by `parse_header_links('<>; rel=empty') == []` (kind: new_behavior)
- **partial-edit**: caught by `parse_header_links('<http://a.example/x>; rel=front, <>; rel=junk, <http://a.example/y>; rel=back') == [{'url': 'http://a.example/x', 'rel': 'front'}, {'url': 'http://a.example/y', 'rel': 'back'}]` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so empty-URL entries continue to appear in the returned list (`no-change`).
- Filters too aggressively (e.g. drops entries when any single param value is empty, not just `url`), breaking the multi-link regression case (`over-edit`).
- Filters at the wrong stage (e.g. drops the entire iteration when one entry has empty `url`, instead of just skipping that one entry), so well-formed neighbouring entries are also lost (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
