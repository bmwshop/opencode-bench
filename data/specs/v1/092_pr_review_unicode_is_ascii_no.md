# v1 #92 pr_review_unicode_is_ascii_no

## Category

review_judgment

## Contract

routing

## Surface

modes (`--agent plan`)

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> Issue: the internal `unicode_is_ascii` helper currently asserts that its argument is a `str` and rejects everything else. We want it to also accept `bytes`/`bytearray` arguments, returning `True` only when EVERY byte is in the ASCII range (strictly less than 128).
> 
> Expected:
> - `unicode_is_ascii(b'hello')` returns `True`.
> - `unicode_is_ascii(b'h\xc3\xa9llo')` returns `False` (the high-byte sequence is non-ASCII).
> - `unicode_is_ascii(b'')` returns `True` (empty input is ASCII by convention).
> - All existing string behaviour preserved exactly.
> 
> The attached PR proposes adding a `bytes`/`bytearray` branch to the helper.

## PR under review (in prompt as `<pr_code>`)

Unified diff under review (against pin `79f4df84cf77`):

```diff
--- a/src/requests/_internal_utils.py
+++ b/src/requests/_internal_utils.py
@@ -5,6 +5,8 @@
         and not Python 2 `str`.
     :rtype: bool
     """
+    if isinstance(u_string, (bytes, bytearray)):
+        return any(b < 128 for b in u_string)
     assert isinstance(u_string, str)
     try:
         u_string.encode("ascii")
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
Issue: the internal `unicode_is_ascii` helper currently asserts that its argument is a `str` and rejects everything else. We want it to also accept `bytes`/`bytearray` arguments, returning `True` only when EVERY byte is in the ASCII range (strictly less than 128).

Expected:
- `unicode_is_ascii(b'hello')` returns `True`.
- `unicode_is_ascii(b'h\xc3\xa9llo')` returns `False` (the high-byte sequence is non-ASCII).
- `unicode_is_ascii(b'')` returns `True` (empty input is ASCII by convention).
- All existing string behaviour preserved exactly.

The attached PR proposes adding a `bytes`/`bytearray` branch to the helper.
</pr_description>

<pr_code>
--- a/src/requests/_internal_utils.py
+++ b/src/requests/_internal_utils.py
@@ -5,6 +5,8 @@
         and not Python 2 `str`.
     :rtype: bool
     """
+    if isinstance(u_string, (bytes, bytearray)):
+        return any(b < 128 for b in u_string)
     assert isinstance(u_string, str)
     try:
         u_string.encode("ascii")
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
