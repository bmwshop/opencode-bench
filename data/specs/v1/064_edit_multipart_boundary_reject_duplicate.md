# v1 #64 edit_multipart_boundary_reject_duplicate

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='extend-comprehension', scope_kind='single-file', answer_shape='raises-with-substring', unique_trait='reject-multiple-boundary-params-keep-first-quote-strip'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `get_multipart_boundary_from_content_type` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_multipart.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `httpx` checkout, the helper that parses an HTTP `Content-Type` header value (as bytes) and returns the multipart `boundary=` parameter currently silently keeps only the *last* boundary it sees when the header contains more than one `boundary=` parameter -- a malformed input that breaks RFC 2046 and is a source of multipart smuggling bugs. Tighten the helper so that:
> 
> - When the input contains two or more `boundary=` parameters, the helper raises `ValueError` whose message contains the substring `boundary`. For example, parsing `b'multipart/form-data; boundary=abc; boundary=xyz'` raises `ValueError`, and parsing `b'multipart/form-data; charset=utf-8; boundary=abc; boundary=xyz'` raises `ValueError`.
> - Existing behaviour on well-formed inputs is preserved exactly: `b'multipart/form-data; boundary=xyz'` returns `b'xyz'`; `b'multipart/form-data; boundary="abc"'` returns `b'abc'` (the surrounding double quotes are still stripped); `b'application/json'` returns `None`; `None` returns `None`; and `b'multipart/form-data'` (no `boundary=` parameter at all) returns `None`.
> 
> The minimal change extends the existing iteration over the `;`-separated sections so that a *second* `boundary=` match triggers a `ValueError` rather than silently overwriting the first match. Do NOT modify the `multipart/form-data` prefix check or the surrounding-quote stripping logic.

## Ground truth (reference edit)

`httpx/_multipart.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    if not content_type or not content_type.startswith(b"multipart/form-data"):
        return None
    # parse boundary according to
    # https://www.rfc-editor.org/rfc/rfc2046#section-5.1.1
    if b";" in content_type:
        for section in content_type.split(b";"):
            if section.strip().lower().startswith(b"boundary="):
                return section.strip()[len(b"boundary=") :].strip(b'"')
    return None
```

```python
# newString
    if not content_type or not content_type.startswith(b"multipart/form-data"):
        return None
    # parse boundary according to
    # https://www.rfc-editor.org/rfc/rfc2046#section-5.1.1
    if b";" in content_type:
        found = None
        for section in content_type.split(b";"):
            if section.strip().lower().startswith(b"boundary="):
                if found is not None:
                    raise ValueError(
                        "get_multipart_boundary_from_content_type: "
                        "content-type contains multiple boundary parameters"
                    )
                found = section.strip()[len(b"boundary=") :].strip(b'"')
        return found
    return None
```


## Hidden truth table (graders only) (N = 7)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `get_multipart_boundary_from_content_type(b'multipart/form-data; boundary=xyz') == b'xyz'` |
| 2 | regression | over-edit | `get_multipart_boundary_from_content_type(b'multipart/form-data; boundary="abc"') == b'abc'` |
| 3 | regression | over-edit | `get_multipart_boundary_from_content_type(b'application/json') is None` |
| 4 | regression | over-edit | `get_multipart_boundary_from_content_type(None) is None` |
| 5 | regression | over-edit | `get_multipart_boundary_from_content_type(b'multipart/form-data') is None` |
| 6 | new_behavior | no-change | `raised is not None and 'boundary' in str(raised)` _(with setup)_ |
| 7 | new_behavior | partial-edit | `raised is not None and 'boundary' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def get_multipart_boundary_from_content_type` -> `httpx/_multipart.py`
- `boundary=` -> `httpx/_content.py`, `httpx/_models.py`, `httpx/_multipart.py`
- `rfc2046` -> `httpx/_multipart.py`

- Union (D = 3): `httpx/_content.py`, `httpx/_models.py`, `httpx/_multipart.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> In this `httpx` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `httpx/`; find it by searching the repo for the behavior described.
> 
> > The target is the small private helper that parses a `Content-Type:` request-header byte string and returns the multipart `boundary=` parameter (used by the multipart streaming code path).
> 
> Behavior contract:
> 
> In this `httpx` checkout, the helper that parses an HTTP `Content-Type` header value (as bytes) and returns the multipart `boundary=` parameter currently silently keeps only the *last* boundary it sees when the header contains more than one `boundary=` parameter -- a malformed input that breaks RFC 2046 and is a source of multipart smuggling bugs. Tighten the helper so that:
> 
> - When the input contains two or more `boundary=` parameters, the helper raises `ValueError` whose message contains the substring `boundary`. For example, parsing `b'multipart/form-data; boundary=abc; boundary=xyz'` raises `ValueError`, and parsing `b'multipart/form-data; charset=utf-8; boundary=abc; boundary=xyz'` raises `ValueError`.
> - Existing behaviour on well-formed inputs is preserved exactly: `b'multipart/form-data; boundary=xyz'` returns `b'xyz'`; `b'multipart/form-data; boundary="abc"'` returns `b'abc'` (the surrounding double quotes are still stripped); `b'application/json'` returns `None`; `None` returns `None`; and `b'multipart/form-data'` (no `boundary=` parameter at all) returns `None`.
> 
> The minimal change extends the existing iteration over the `;`-separated sections so that a *second* `boundary=` match triggers a `ValueError` rather than silently overwriting the first match. Do NOT modify the `multipart/form-data` prefix check or the surrounding-quote stripping logic.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_multipart.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `get_multipart_boundary_from_content_type(b'multipart/form-data; boundary=xyz') == b'xyz'` (kind: regression)
- **over-edit**: caught by `get_multipart_boundary_from_content_type(b'multipart/form-data; boundary="abc"') == b'abc'` (kind: regression)
- **over-edit**: caught by `get_multipart_boundary_from_content_type(b'application/json') is None` (kind: regression)
- **over-edit**: caught by `get_multipart_boundary_from_content_type(None) is None` (kind: regression)
- **over-edit**: caught by `get_multipart_boundary_from_content_type(b'multipart/form-data') is None` (kind: regression)
- **no-change**: caught by `raised is not None and 'boundary' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and 'boundary' in str(raised)` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so a duplicate `boundary=` parameter is silently overwritten and only the last one wins (`no-change`).
- Raises `ValueError` on duplicates but also tightens the prefix check so plain `b'multipart/form-data'` (no boundary at all) raises instead of returning `None`, breaking a regression case (`over-edit`).
- Detects duplicates but raises a different exception class (e.g. `RuntimeError`) or omits the `boundary` substring from the message (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
