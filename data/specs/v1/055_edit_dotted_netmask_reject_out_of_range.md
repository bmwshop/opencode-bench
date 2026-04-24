# v1 #55 edit_dotted_netmask_reject_out_of_range

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `dotted_netmask` (plus in-file callees: _(none)_)
- Target file: `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

```python
# oldString
def dotted_netmask(mask):
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0

    :rtype: str
    """
    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))
```

```python
# newString
def dotted_netmask(mask):
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0

    :rtype: str
    """
    if not isinstance(mask, int) or isinstance(mask, bool) or mask < 0 or mask > 32:
        raise ValueError(f"dotted_netmask: mask must be an int in [0, 32], got {mask!r}")
    if mask == 0:
        bits = 0
    else:
        bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))
```

## Truth table (N = 6)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `dotted_netmask(24) == '255.255.255.0'` |
| 2 | regression | over-edit | `dotted_netmask(16) == '255.255.0.0'` |
| 3 | regression | over-edit | `dotted_netmask(32) == '255.255.255.255'` |
| 4 | regression | partial-edit | `dotted_netmask(0) == '0.0.0.0'` |
| 5 | new_behavior | no-change | `raised is not None and 'mask' in str(raised)` _(with setup)_ |
| 6 | new_behavior | partial-edit | `raised is not None and 'mask' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def dotted_netmask` -> `src/requests/utils.py`
- `netmask` -> `src/requests/utils.py`
- `network` -> `src/requests/models.py`, `src/requests/status_codes.py`, `src/requests/utils.py`

- Union (D = 3): `src/requests/models.py`, `src/requests/status_codes.py`, `src/requests/utils.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`dotted_netmask`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `dotted_netmask` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target converts an integer CIDR mask length (e.g. 24) into its dotted-quad representation (e.g. `'255.255.255.0'`). It lives in the `requests` utilities module alongside other small IP-address helpers.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert dotted_netmask(24) == '255.255.255.0'
>     assert dotted_netmask(16) == '255.255.0.0'
>     assert dotted_netmask(32) == '255.255.255.255'
>     assert dotted_netmask(0) == '0.0.0.0'
>     # setup: raised = None ; try: ; dotted_netmask(-1) ; except ValueError as e: ; raised = e
>     assert raised is not None and 'mask' in str(raised)
>     # setup: raised = None ; try: ; dotted_netmask(33) ; except ValueError as e: ; raised = e
>     assert raised is not None and 'mask' in str(raised)
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every regression assert; do not delete existing behavior.
> - Use the exact exception class names that appear in the assertions above (e.g. `ValueError`, `TypeError`) -- other classes will not satisfy the asserts.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` `src/requests/utils.py` - every entry in the truth table above evaluates True against the patched file (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `dotted_netmask(24) == '255.255.255.0'` (kind: regression)
- **over-edit**: caught by `dotted_netmask(16) == '255.255.0.0'` (kind: regression)
- **over-edit**: caught by `dotted_netmask(32) == '255.255.255.255'` (kind: regression)
- **partial-edit**: caught by `dotted_netmask(0) == '0.0.0.0'` (kind: regression)
- **no-change**: caught by `raised is not None and 'mask' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and 'mask' in str(raised)` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so out-of-range masks silently produce garbage (no ValueError) (`no-change`).
- Adds a range check but also restricts the valid range (e.g. `[1, 32]` rather than `[0, 32]`), breaking the `dotted_netmask(0) == '0.0.0.0'` assert (`partial-edit`).
- Raises `ValueError` but forgets to also return `'0.0.0.0'` for mask 0 (the bit-twiddling `1 << 32` overflows or produces wrong bits on `mask=0`) (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
