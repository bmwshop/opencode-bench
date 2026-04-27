# v1 #57 edit_is_valid_cidr_accept_zero_mask

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='loosen-bound', scope_kind='single-file', answer_shape='value-equality', unique_trait='accept-zero-mask-reject-negative'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `is_valid_cidr` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, the predicate used by `no_proxy` matching to validate a CIDR network string (e.g. `10.0.0.0/8`) currently rejects the all-routes mask `/0`. Loosen the predicate so that:
> 
> - A mask of `0` is now valid: `'0.0.0.0/0'` returns `True` and `'10.0.0.0/0'` returns `True`.
> - Negative masks remain invalid: `'192.168.1.0/-1'` returns `False`.
> - All existing rejections are preserved: `'192.168.1.0/33'` returns `False`, `'not-a-cidr'` returns `False`, and `'192.168.1.0'` (no mask, no `/`) returns `False`.
> - All existing acceptances are preserved: `'192.168.1.0/24'` returns `True` and `'10.0.0.0/8'` returns `True`.
> 
> The predicate lives in the `requests` utilities module alongside other small IP-address helpers and is invoked while parsing the `no_proxy` environment variable; locate it by searching for the comment about `cidr format` or for the `no_proxy` keyword.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
        if mask < 1 or mask > 32:
            return False
```

```python
# newString
        if mask < 0 or mask > 32:
            return False
```


## Hidden truth table (graders only) (N = 8)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `is_valid_cidr('192.168.1.0/24') is True` |
| 2 | regression | over-edit | `is_valid_cidr('10.0.0.0/8') is True` |
| 3 | regression | over-edit | `is_valid_cidr('192.168.1.0/33') is False` |
| 4 | regression | over-edit | `is_valid_cidr('not-a-cidr') is False` |
| 5 | regression | over-edit | `is_valid_cidr('192.168.1.0') is False` |
| 6 | new_behavior | no-change | `is_valid_cidr('0.0.0.0/0') is True` |
| 7 | new_behavior | partial-edit | `is_valid_cidr('10.0.0.0/0') is True` |
| 8 | new_behavior | over-edit | `is_valid_cidr('192.168.1.0/-1') is False` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def is_valid_cidr` -> `src/requests/utils.py`
- `Very simple check of the cidr format` -> `src/requests/utils.py`
- `no_proxy` -> `src/requests/sessions.py`, `src/requests/utils.py`

- Union (D = 2): `src/requests/sessions.py`, `src/requests/utils.py`

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

1. `exec_assert` (`src/requests/utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `is_valid_cidr('192.168.1.0/24') is True` (kind: regression)
- **over-edit**: caught by `is_valid_cidr('10.0.0.0/8') is True` (kind: regression)
- **over-edit**: caught by `is_valid_cidr('192.168.1.0/33') is False` (kind: regression)
- **over-edit**: caught by `is_valid_cidr('not-a-cidr') is False` (kind: regression)
- **over-edit**: caught by `is_valid_cidr('192.168.1.0') is False` (kind: regression)
- **no-change**: caught by `is_valid_cidr('0.0.0.0/0') is True` (kind: new_behavior)
- **partial-edit**: caught by `is_valid_cidr('10.0.0.0/0') is True` (kind: new_behavior)
- **over-edit**: caught by `is_valid_cidr('192.168.1.0/-1') is False` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `/0` is still rejected (`no-change`).
- Accepts `/0` but also silently accepts `/-1` (e.g. by dropping the lower bound entirely) (`over-edit`).
- Accepts `/0` only for `0.0.0.0` but still rejects `10.0.0.0/0`, e.g. by coupling the change to the IP value rather than the mask (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
