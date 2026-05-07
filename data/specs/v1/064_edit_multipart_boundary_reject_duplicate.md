# v1 #64 edit_multipart_boundary_reject_duplicate

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

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

1. `exec_assert` (`httpx/_multipart.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so a duplicate `boundary=` parameter is silently overwritten and only the last one wins (`no-change`).
- Raises `ValueError` on duplicates but also tightens the prefix check so plain `b'multipart/form-data'` (no boundary at all) raises instead of returning `None`, breaking a regression case (`over-edit`).
- Detects duplicates but raises a different exception class (e.g. `RuntimeError`) or omits the `boundary` substring from the message (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
