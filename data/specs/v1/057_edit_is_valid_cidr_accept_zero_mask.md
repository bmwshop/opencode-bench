# v1 #57 edit_is_valid_cidr_accept_zero_mask

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `src/requests/`; find it by searching the repo for the behavior described.
> 
> > The target is the predicate used by `no_proxy` matching to check whether a string looks like a valid CIDR network (e.g. `10.0.0.0/8`). It lives in the `requests` utilities module alongside other small IP-address helpers.
> 
> Behavior contract:
> 
> In this `requests` checkout, the predicate used by `no_proxy` matching to validate a CIDR network string (e.g. `10.0.0.0/8`) currently rejects the all-routes mask `/0`. Loosen the predicate so that:
> 
> - A mask of `0` is now valid: `'0.0.0.0/0'` returns `True` and `'10.0.0.0/0'` returns `True`.
> - Negative masks remain invalid: `'192.168.1.0/-1'` returns `False`.
> - All existing rejections are preserved: `'192.168.1.0/33'` returns `False`, `'not-a-cidr'` returns `False`, and `'192.168.1.0'` (no mask, no `/`) returns `False`.
> - All existing acceptances are preserved: `'192.168.1.0/24'` returns `True` and `'10.0.0.0/8'` returns `True`.
> 
> The predicate lives in the `requests` utilities module alongside other small IP-address helpers and is invoked while parsing the `no_proxy` environment variable; locate it by searching for the comment about `cidr format` or for the `no_proxy` keyword.
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

- Leaves the function unchanged, so `/0` is still rejected (`no-change`).
- Accepts `/0` but also silently accepts `/-1` (e.g. by dropping the lower bound entirely) (`over-edit`).
- Accepts `/0` only for `0.0.0.0` but still rejects `10.0.0.0/0`, e.g. by coupling the change to the IP value rather than the mask (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
