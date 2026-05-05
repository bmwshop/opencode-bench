# v1 #94 pr_review_unquote_header_value_no

## Category

code_review

## Contract

routing

## Surface

modes (`--agent plan`)

## Paper reference

Ma et al., arXiv:2604.05013, Appendix E. The agent acts as a code reviewer:
given a PR description + PR diff, it explores the repo read-only and emits a
structured `<judgment>YES|NO</judgment>` plus a `<review>` summary.

## Source cross-reference

This sample reuses material from the `code_editing` source manifest (no new bugs authored):

- source_manifest: `data/v1_editing_criteria.json`
- source_id: **#54** (edit_unquote_header_value_none_returns_empty)
- variant: **mutants[0]**
- gold label: **NO**

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> Issue: `unquote_header_value` in the requests utilities module crashes with `TypeError` when given `None` (it indexes the value before any guard). It should tolerate `None` and return the empty string -- both with and without the `is_filename=True` flag.
> 
> Expected:
> - `unquote_header_value(None) == ''`
> - `unquote_header_value(None, is_filename=True) == ''`
> - All existing string-input behaviour preserved exactly (`'"hello"'` -> `'hello'`; `'hello'` -> `'hello'`; `''` -> `''`; `'"hello world"'` -> `'hello world'`).
> 
> The attached PR adds an early-return guard for the None case.

## PR under review (in prompt as `<pr_code>`)

Unified diff constructed from the source manifest's `mutants[0]` for source #54, against pin `79f4df84cf77`:

```diff
--- a/src/requests/utils.py
+++ b/src/requests/utils.py
@@ -6,4 +6,6 @@
     :param value: the header value to unquote.
     :rtype: str
     """
+    if value is None:
+        return None
     if value and value[0] == value[-1] == '"':
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
Issue: `unquote_header_value` in the requests utilities module crashes with `TypeError` when given `None` (it indexes the value before any guard). It should tolerate `None` and return the empty string -- both with and without the `is_filename=True` flag.

Expected:
- `unquote_header_value(None) == ''`
- `unquote_header_value(None, is_filename=True) == ''`
- All existing string-input behaviour preserved exactly (`'"hello"'` -> `'hello'`; `'hello'` -> `'hello'`; `''` -> `''`; `'"hello world"'` -> `'hello world'`).

The attached PR adds an early-return guard for the None case.
</pr_description>

<pr_code>
--- a/src/requests/utils.py
+++ b/src/requests/utils.py
@@ -6,4 +6,6 @@
     :param value: the header value to unquote.
     :rtype: str
     """
+    if value is None:
+        return None
     if value and value[0] == value[-1] == '"':
</pr_code>

Review the pr_code to determine whether it correctly fixes the issue described above. After your review, provide:

<review>
Your detailed review. Cite specific lines or functions where relevant.
</review>

<judgment>
YES or NO
</judgment>

Use "YES" if the pr_code correctly fixes the issue. Use "NO" if it does not.
```

## Pass criteria (4 checks)

1. `no_tool_name` not in `[edit, bash, write]` — plan-mode adherence (the agent must not modify files or execute code)
2. `text_contains` `<judgment>\s*NO\s*</judgment>` — gold-gated structured judgment
3. `text_contains` `<review>[\s\S]*?</review>` — non-empty `<review>` block (structured-output discipline)
4. `call_schema_valid` — every read/grep/glob call matches opencode's canonical JSON schemas

## Label oracle (graders only)

Mechanical proof that label = `NO` is correct: apply the mutants[0] patch from source #54 on top of the pinned baseline, then run `exec_assert` against the source's truth table. The label must match the outcome:

- `label=YES` -> exec_assert PASSES (all asserts in source.asserts evaluate True)
- `label=NO` -> exec_assert FAILS at least one assert

Verified mechanically by `python3 data/scripts/audit_review.py --id 94` (Pass 1).

## Shortest path

**1-3 tool calls**: read the affected file(s) under `src/requests/` (typically 1 read for single-file diffs, 2 for multi-file), then synthesize the judgment in the response. The diff is already in the prompt; the agent's job is to verify it actually addresses the issue.

## Fail modes

- Uses `edit` / `write` / `bash` -- violates plan-mode (check 1).
- Outputs the wrong judgment for the gold label (check 2).
- Forgets the `<review>` block (check 3).
- Malformed read-tool args (check 4).
- Confidently judges YES/NO without reading the actual source -- not directly checked, but the issue text deliberately omits enough detail that a no-read judgment is unreliable.

## Intentionally *not* checked

- Free-form text in `<review>` -- the review summary is required by the prompt (per the paper) but its content is not graded.
- Whether the agent uses `read`, `grep`, or `glob` -- any read-only tool mix is acceptable.
- Number of tool calls -- plan mode samples have `min_calls: 0` (a confident reader can skip exploration).

## Note on methodology

This sample is the paper-faithful `code_review` atomic skill (Ma et al. arXiv:2604.05013), implemented via cross-reference to the `code_editing` source manifest. The PR diff is constructed mechanically; the gold label is mechanically derived from `exec_assert` against the source's truth table. The agent's role is to JUDGE, not to PATCH.

If the source manifest changes, re-run `data/scripts/regen_review.py` and `data/scripts/audit_review.py`.

## Lock-in hash

SHA-256 of `(source_manifest, source_id, variant, label, issue_text)` JSON-serialized with sorted keys. Drift in any of these fields changes the hash. Cross-referenced in [data/scripts/docs/v1_review_lock_in.md](../../scripts/docs/v1_review_lock_in.md).

`4120664a2d40093ad1f93bcef60bdc5ed547bd75a0bab543fc9d4fcc0ea899e8`
