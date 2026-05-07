# v1 #97 pr_review_is_valid_cidr_yes

## Category

review_judgment

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

- source_manifest: v1 editing criteria manifest
- source_id: **#57** (edit_is_valid_cidr_accept_zero_mask)
- variant: **reference_edit**
- gold label: **YES**

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> Issue: the predicate that validates a CIDR network string (used by the `no_proxy` matcher in the requests utilities module) currently rejects the all-routes mask `/0`, even though that's a perfectly valid CIDR notation.
> 
> Expected:
> - `'0.0.0.0/0'` returns `True`.
> - `'10.0.0.0/0'` returns `True`.
> - `'192.168.1.0/-1'` continues to return `False` (negative masks remain invalid).
> - `'192.168.1.0/33'` continues to return `False` (out-of-range masks remain invalid).
> - `'not-a-cidr'` and `'192.168.1.0'` (no `/`) continue to return `False`.
> - All existing acceptances preserved (`'192.168.1.0/24'`, `'10.0.0.0/8'`).
> 
> The attached PR loosens the mask-range check accordingly.

## PR under review (in prompt as `<pr_code>`)

Unified diff constructed from the source manifest's `reference_edit` for source #57, against pin `79f4df84cf77`:

```diff
--- a/src/requests/utils.py
+++ b/src/requests/utils.py
@@ -1,2 +1,2 @@
-        if mask < 1 or mask > 32:
+        if mask < 0 or mask > 32:
             return False
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
Issue: the predicate that validates a CIDR network string (used by the `no_proxy` matcher in the requests utilities module) currently rejects the all-routes mask `/0`, even though that's a perfectly valid CIDR notation.

Expected:
- `'0.0.0.0/0'` returns `True`.
- `'10.0.0.0/0'` returns `True`.
- `'192.168.1.0/-1'` continues to return `False` (negative masks remain invalid).
- `'192.168.1.0/33'` continues to return `False` (out-of-range masks remain invalid).
- `'not-a-cidr'` and `'192.168.1.0'` (no `/`) continue to return `False`.
- All existing acceptances preserved (`'192.168.1.0/24'`, `'10.0.0.0/8'`).

The attached PR loosens the mask-range check accordingly.
</pr_description>

<pr_code>
--- a/src/requests/utils.py
+++ b/src/requests/utils.py
@@ -1,2 +1,2 @@
-        if mask < 1 or mask > 32:
+        if mask < 0 or mask > 32:
             return False
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
2. `text_contains` `<judgment>\s*YES\s*</judgment>` — gold-gated structured judgment
3. `text_contains` `<review>[\s\S]*?</review>` — non-empty `<review>` block (structured-output discipline)
4. `call_schema_valid` — every read/grep/glob call matches opencode's canonical JSON schemas

## Label oracle (graders only)

Mechanical proof that label = `YES` is correct: apply the reference_edit patch from source #57 on top of the pinned baseline, then run `exec_assert` against the source's truth table. The label must match the outcome:

- `label=YES` -> exec_assert PASSES (all asserts in source.asserts evaluate True)
- `label=NO` -> exec_assert FAILS at least one assert

Verified mechanically by the review audit procedure (Pass 1).

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

This sample is the paper-faithful `review_judgment` atomic skill (Ma et al. arXiv:2604.05013), implemented via cross-reference to the `code_editing` source manifest. The PR diff is constructed mechanically; the gold label is mechanically derived from `exec_assert` against the source's truth table. The agent's role is to JUDGE, not to PATCH.

If the source manifest changes, re-run the review regeneration and audit procedure.

## Lock-in hash

SHA-256 of `(source_manifest, source_id, variant, label, issue_text)` JSON-serialized with sorted keys. Drift in any of these fields changes the hash. Cross-referenced in the v1 review lock-in record.

`611e0e05a449e1e8a9a04e5c16cf8e37d8c87dba07f9dc40b1477314358678fb`
