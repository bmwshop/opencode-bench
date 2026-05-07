# v1 #61 edit_is_known_encoding_typecheck

## Category

code_editing

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Prompt

> Modify the function `_is_known_encoding` inside the `httpx` package so that the behavior contract below holds:
> 
> > The target is the small private helper `_is_known_encoding` declared at module scope inside `httpx`. It currently accepts any value, calls `codecs.lookup` on it, and returns `True`/`False` based on whether a `LookupError` is raised; with non-string input it instead crashes with `TypeError` from inside `codecs.lookup`.
> 
> Behavior contract:
> 
> Modify the function `_is_known_encoding` (declared at module scope inside `httpx`) so that it gracefully rejects non-string inputs:
> 
> - Calling `_is_known_encoding(x)` where `x` is not a `str` instance now raises `ValueError` whose message contains the substring `encoding`. For example, `_is_known_encoding(123)` raises `ValueError`, and `_is_known_encoding(None)` raises `ValueError`.
> - Existing behaviour on string inputs is preserved exactly: `_is_known_encoding('utf-8')` returns `True`, `_is_known_encoding('utf-16')` returns `True`, and `_is_known_encoding('not-a-real-codec')` returns `False`.
> 
> The minimal change is a single guard at the top of the function body that runs before `codecs.lookup` is called; do NOT change the existing `codecs.lookup` / `LookupError` logic.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_models.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so non-string input still crashes with TypeError from inside codecs.lookup (`no-change`).
- Catches the TypeError inside the existing try/except instead of raising ValueError up front, returning False on non-string input rather than raising (`partial-edit`).
- Raises ValueError but only for one specific non-string class (e.g. `int`), so other non-string inputs like `None` still crash (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
