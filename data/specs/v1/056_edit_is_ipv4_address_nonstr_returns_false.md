# v1 #56 edit_is_ipv4_address_nonstr_returns_false

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `is_ipv4_address` (plus in-file callees: _(none)_)
- Target file: `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

```python
# oldString
def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True
```

```python
# newString
def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    if not isinstance(string_ip, str):
        return False
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True
```

## Truth table (N = 7)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `is_ipv4_address('192.168.1.1') is True` |
| 2 | regression | over-edit | `is_ipv4_address('10.0.0.0') is True` |
| 3 | regression | over-edit | `is_ipv4_address('not-an-ip') is False` |
| 4 | regression | over-edit | `is_ipv4_address('256.1.1.1') is False` |
| 5 | new_behavior | no-change | `is_ipv4_address(None) is False` |
| 6 | new_behavior | partial-edit | `is_ipv4_address(123) is False` |
| 7 | new_behavior | partial-edit | `is_ipv4_address(b'192.168.1.1') is False` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def is_ipv4_address` -> `src/requests/utils.py`
- `IPv4` -> _(no match)_
- `network` -> `src/requests/models.py`, `src/requests/status_codes.py`, `src/requests/utils.py`

- Union (D = 3): `src/requests/models.py`, `src/requests/status_codes.py`, `src/requests/utils.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`is_ipv4_address`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `is_ipv4_address` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the predicate that tests whether a value is a valid textual IPv4 address. It lives in the `requests` utilities module alongside other small IP-address helpers.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert is_ipv4_address('192.168.1.1') is True
>     assert is_ipv4_address('10.0.0.0') is True
>     assert is_ipv4_address('not-an-ip') is False
>     assert is_ipv4_address('256.1.1.1') is False
>     assert is_ipv4_address(None) is False
>     assert is_ipv4_address(123) is False
>     assert is_ipv4_address(b'192.168.1.1') is False
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

- **no-change**: caught by `is_ipv4_address('192.168.1.1') is True` (kind: regression)
- **over-edit**: caught by `is_ipv4_address('10.0.0.0') is True` (kind: regression)
- **over-edit**: caught by `is_ipv4_address('not-an-ip') is False` (kind: regression)
- **over-edit**: caught by `is_ipv4_address('256.1.1.1') is False` (kind: regression)
- **no-change**: caught by `is_ipv4_address(None) is False` (kind: new_behavior)
- **partial-edit**: caught by `is_ipv4_address(123) is False` (kind: new_behavior)
- **partial-edit**: caught by `is_ipv4_address(b'192.168.1.1') is False` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so passing `None`/`int`/`bytes` crashes with `TypeError` instead of returning False (`no-change`).
- Catches all exceptions (`except Exception`) to mask the bug, which also silences genuine bugs in the body (`over-edit`).
- Accepts `bytes` as valid (because `socket.inet_aton` does accept bytes on some platforms) instead of rejecting everything that's not `str` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
