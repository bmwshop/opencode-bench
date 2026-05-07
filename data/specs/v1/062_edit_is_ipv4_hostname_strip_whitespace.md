# v1 #62 edit_is_ipv4_hostname_strip_whitespace

## Category

code_editing

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Prompt

> Modify the function `is_ipv4_hostname` inside the `httpx` package so that the behavior contract below holds:
> 
> > The target is the small `is_ipv4_hostname` predicate declared at module scope inside `httpx`. It currently calls `hostname.split('/')[0]` directly; the `IPv4Address` parser then rejects any input with stray leading/trailing whitespace, so an otherwise-valid hostname like `'  1.2.3.4  '` returns `False`.
> 
> Behavior contract:
> 
> Modify the function `is_ipv4_hostname` (declared at module scope inside `httpx`) so that surrounding whitespace on the input is tolerated:
> 
> - Calling `is_ipv4_hostname(s)` with leading or trailing whitespace (spaces, tabs, newlines) on an otherwise valid IPv4 hostname now returns `True`. For example, `is_ipv4_hostname('   1.2.3.4   ')` returns `True`, and `is_ipv4_hostname('\t1.2.3.4/32\n')` returns `True`.
> - Existing behaviour on whitespace-free inputs is preserved exactly: `is_ipv4_hostname('1.2.3.4')` returns `True`; the trailing CIDR mask is still stripped before the address parse, so `is_ipv4_hostname('1.2.3.4/32')` returns `True`; `is_ipv4_hostname('not-an-ip')` returns `False`; `is_ipv4_hostname('')` returns `False`.
> 
> The minimal change normalises whitespace on the input before the existing CIDR-stripping `.split('/')` call. Do NOT change the existing `IPv4Address` parse logic or the `except Exception: return False` fallback.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so `is_ipv4_hostname('  1.2.3.4  ')` still returns `False` because the `IPv4Address` parser rejects whitespace (`no-change`).
- Strips whitespace from the input but only for the leading side (e.g. `lstrip()` instead of `strip()`), so trailing-whitespace inputs still return `False` (`partial-edit`).
- Strips whitespace globally (e.g. removes all internal spaces too), accidentally accepting malformed inputs like `'1.2 . 3 . 4'` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
