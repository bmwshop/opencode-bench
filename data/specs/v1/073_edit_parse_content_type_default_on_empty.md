# v1 #73 edit_parse_content_type_default_on_empty

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='default-on-empty-content-type', scope_kind='single-file', answer_shape='value-equality', unique_trait='fallback-to-octet-stream-when-leading-semicolon-or-empty-content-type'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `_parse_content_type_header` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the small private helper that parses a `Content-Type` header byte string into a `(content_type, params_dict)` tuple returns the empty string `''` for the content-type whenever the header starts with a `;` (so that the leading `;`-split token is empty). Downstream code like `get_encoding_from_headers` then tests `'text' in content_type`, which matches `''` only via fallback heuristics that are clearly wrong. Tighten the helper so that:
> 
> - When the leading content-type token would otherwise be the empty string, the helper returns `'application/octet-stream'` as the content-type instead. For example, parsing `;charset=utf-8` returns `('application/octet-stream', {'charset': 'utf-8'})`.
> - The params dict still parses normally for the leading-`;` case: parsing `;charset=utf-8` still produces `{'charset': 'utf-8'}`.
> - Existing behaviour on inputs that have a leading content-type is preserved exactly: parsing `text/html` returns `('text/html', {})`; parsing `text/html; charset=utf-8` produces `'text/html'` plus a `{'charset': 'utf-8'}` dict; parsing `application/json; charset="utf-8"; boundary=abc` produces `'application/json'` plus a `{'charset': 'utf-8', 'boundary': 'abc'}` dict (existing surrounding-quote stripping still applies); and a bare `application/octet-stream` (no params) returns `('application/octet-stream', {})`.
> 
> The minimal change is a single guard inserted between the `tokens[0].strip()` line and the `params_dict = {}` line that reassigns `content_type` to `'application/octet-stream'` when it is otherwise the empty string. Do NOT modify the parameter-parsing loop or its `strip_chars` handling. The helper lives among the small header-parsing helpers under `src/requests/`; locate it by searching for `content_type` or `charset` references in the codebase.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    strip_chars = "\"' "

    for param in params:
        param = param.strip()
        if param and (idx := param.find("=")) != -1:
            key = param[:idx].strip(strip_chars)
            value = param[idx + 1 :].strip(strip_chars)
            params_dict[key.lower()] = value
    return content_type, params_dict
```

```python
# newString
    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    if not content_type:
        content_type = "application/octet-stream"
    params_dict = {}
    strip_chars = "\"' "

    for param in params:
        param = param.strip()
        if param and (idx := param.find("=")) != -1:
            key = param[:idx].strip(strip_chars)
            value = param[idx + 1 :].strip(strip_chars)
            params_dict[key.lower()] = value
    return content_type, params_dict
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `_parse_content_type_header('text/html')[0] == 'text/html'` |
| 2 | regression | over-edit | `_parse_content_type_header('text/html; charset=utf-8')[1] == {'charset': 'utf-8'}` |
| 3 | regression | over-edit | `_parse_content_type_header('application/json; charset="utf-8"; boundary=abc')[1] == {'charset': 'utf-8', 'boundary': 'abc'}` |
| 4 | regression | over-edit | `_parse_content_type_header('application/octet-stream') == ('application/octet-stream', {})` |
| 5 | new_behavior | no-change | `_parse_content_type_header(';charset=utf-8')[0] == 'application/octet-stream'` |
| 6 | new_behavior | partial-edit | `_parse_content_type_header(';charset=utf-8')[1] == {'charset': 'utf-8'}` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def _parse_content_type_header` -> `src/requests/utils.py`
- `parse_dict_header` -> `src/requests/auth.py`, `src/requests/utils.py`
- `get_encoding_from_headers` -> `src/requests/adapters.py`, `src/requests/utils.py`

- Union (D = 3): `src/requests/adapters.py`, `src/requests/auth.py`, `src/requests/utils.py`

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
> > The target is the small private helper inside `requests` that splits a `Content-Type` header value on `;`, returns the leading content-type token and a dict of parameters (e.g. `charset`, `boundary`). Today, when the header has no leading content-type token (it starts with a `;`, leaving `tokens[0]` as `''`), the helper returns an empty string for the content-type. Downstream consumers like `get_encoding_from_headers` then test substrings (`'text' in content_type`) against the empty string and produce confusing fallback behaviour.
> 
> Behavior contract:
> 
> In this `requests` checkout, the small private helper that parses a `Content-Type` header byte string into a `(content_type, params_dict)` tuple returns the empty string `''` for the content-type whenever the header starts with a `;` (so that the leading `;`-split token is empty). Downstream code like `get_encoding_from_headers` then tests `'text' in content_type`, which matches `''` only via fallback heuristics that are clearly wrong. Tighten the helper so that:
> 
> - When the leading content-type token would otherwise be the empty string, the helper returns `'application/octet-stream'` as the content-type instead. For example, parsing `;charset=utf-8` returns `('application/octet-stream', {'charset': 'utf-8'})`.
> - The params dict still parses normally for the leading-`;` case: parsing `;charset=utf-8` still produces `{'charset': 'utf-8'}`.
> - Existing behaviour on inputs that have a leading content-type is preserved exactly: parsing `text/html` returns `('text/html', {})`; parsing `text/html; charset=utf-8` produces `'text/html'` plus a `{'charset': 'utf-8'}` dict; parsing `application/json; charset="utf-8"; boundary=abc` produces `'application/json'` plus a `{'charset': 'utf-8', 'boundary': 'abc'}` dict (existing surrounding-quote stripping still applies); and a bare `application/octet-stream` (no params) returns `('application/octet-stream', {})`.
> 
> The minimal change is a single guard inserted between the `tokens[0].strip()` line and the `params_dict = {}` line that reassigns `content_type` to `'application/octet-stream'` when it is otherwise the empty string. Do NOT modify the parameter-parsing loop or its `strip_chars` handling. The helper lives among the small header-parsing helpers under `src/requests/`; locate it by searching for `content_type` or `charset` references in the codebase.
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

- **no-change**: caught by `_parse_content_type_header('text/html')[0] == 'text/html'` (kind: regression)
- **over-edit**: caught by `_parse_content_type_header('text/html; charset=utf-8')[1] == {'charset': 'utf-8'}` (kind: regression)
- **over-edit**: caught by `_parse_content_type_header('application/json; charset="utf-8"; boundary=abc')[1] == {'charset': 'utf-8', 'boundary': 'abc'}` (kind: regression)
- **over-edit**: caught by `_parse_content_type_header('application/octet-stream') == ('application/octet-stream', {})` (kind: regression)
- **no-change**: caught by `_parse_content_type_header(';charset=utf-8')[0] == 'application/octet-stream'` (kind: new_behavior)
- **partial-edit**: caught by `_parse_content_type_header(';charset=utf-8')[1] == {'charset': 'utf-8'}` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so a leading-`;` input still produces an empty-string content-type that pollutes downstream encoding detection (`no-change`).
- Replaces the empty content-type with the wrong default (e.g. `'text/plain'`), satisfying the leading-`;` case but accidentally also matching the `'text' in content_type` heuristic in `get_encoding_from_headers` and over-applying the `ISO-8859-1` fallback (`partial-edit`).
- Always overwrites the content-type with `'application/octet-stream'` (not just when it would be empty), so a valid `text/html` input now also returns `'application/octet-stream'` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
