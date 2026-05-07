# v1 #56 edit_is_ipv4_address_nonstr_returns_false

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> Modify the function `is_ipv4_address` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the predicate `is_ipv4_address` that tests whether a value is a valid textual IPv4 address. It lives in the `requests` utilities module alongside other small IP-address helpers.
> 
> Behavior contract:
> 
> Modify the function `is_ipv4_address` (declared at module scope inside the `requests` utilities module) so that it returns `False` (rather than raising `TypeError`) for any non-`str` input, while preserving its existing behaviour on string inputs:
> 
> - `is_ipv4_address(None)` now returns `False`.
> - `is_ipv4_address(123)` (any non-string integer) returns `False`.
> - `is_ipv4_address(b'192.168.1.1')` (bytes value) returns `False`.
> - All existing behaviour on string inputs is preserved exactly: `'192.168.1.1'` returns `True`, `'10.0.0.0'` returns `True`, `'not-an-ip'` returns `False`, and `'256.1.1.1'` returns `False`.
> 
> The minimal change is a single early-return guard at the top of the function body that checks `isinstance(string_ip, str)`. Do NOT broaden the guard to use `try`/`except Exception` (that masks genuine bugs).
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

- Leaves the function unchanged, so passing `None`/`int`/`bytes` crashes with `TypeError` instead of returning False (`no-change`).
- Catches all exceptions (`except Exception`) to mask the bug, which also silences genuine bugs in the body (`over-edit`).
- Accepts `bytes` as valid (because `socket.inet_aton` does accept bytes on some platforms) instead of rejecting everything that's not `str` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
