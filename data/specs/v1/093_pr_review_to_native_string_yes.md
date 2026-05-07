# v1 #93 pr_review_to_native_string_yes

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

- source_manifest: `data/v1_editing_criteria.json`
- source_id: **#53** (edit_to_native_string_reject_unknown_with_caller)
- variant: **reference_edit**
- gold label: **YES**

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> Issue (cross-cutting): two related defensive holes in our internal helpers.
> 
> 1. `to_native_string` in the internal-utils module currently crashes with `AttributeError` when given a non-string, non-bytes input (e.g. an `int`). It should reject those inputs cleanly with `TypeError` whose message contains the substring `str or bytes`.
> 
> 2. The basic-authentication helper that builds an HTTP `Basic <base64>` header treats a `None` username or `None` password by emitting a deprecation warning and `str(...)`-coercing them to the literal four-character string `'None'` -- which encodes nonsense. It should treat a `None` username/password as the empty bytes value `b''` instead. Concretely: `(None, 'pw')` should yield `'Basic OnB3'` and `(None, None)` should yield `'Basic Og=='`. The existing deprecation-warning path for non-`None`, non-string inputs (e.g. an integer) must be preserved.
> 
> The attached PR touches both files in one go.

## PR under review (in prompt as `<pr_code>`)

Unified diff constructed from the source manifest's `reference_edit` for source #53, against pin `79f4df84cf77`:

```diff
--- a/src/requests/_internal_utils.py
+++ b/src/requests/_internal_utils.py
@@ -4,8 +4,9 @@
     necessary. This assumes ASCII unless told otherwise.
     """
     if isinstance(string, builtin_str):
-        out = string
-    else:
-        out = string.decode(encoding)
-
-    return out
+        return string
+    if isinstance(string, (bytes, bytearray)):
+        return bytes(string).decode(encoding)
+    raise TypeError(
+        f"to_native_string expected str or bytes, got {type(string).__name__}"
+    )
--- a/src/requests/auth.py
+++ b/src/requests/auth.py
@@ -1,4 +1,6 @@
-    if not isinstance(username, basestring):
+    if username is None:
+        username = b""
+    elif not isinstance(username, basestring):
         warnings.warn(
             "Non-string usernames will no longer be supported in Requests "
             f"3.0.0. Please convert the object you've passed in ({username!r}) to "
@@ -8,7 +10,9 @@
         )
         username = str(username)
 
-    if not isinstance(password, basestring):
+    if password is None:
+        password = b""
+    elif not isinstance(password, basestring):
         warnings.warn(
             "Non-string passwords will no longer be supported in Requests "
             f"3.0.0. Please convert the object you've passed in ({type(password)!r}) to "
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
Issue (cross-cutting): two related defensive holes in our internal helpers.

1. `to_native_string` in the internal-utils module currently crashes with `AttributeError` when given a non-string, non-bytes input (e.g. an `int`). It should reject those inputs cleanly with `TypeError` whose message contains the substring `str or bytes`.

2. The basic-authentication helper that builds an HTTP `Basic <base64>` header treats a `None` username or `None` password by emitting a deprecation warning and `str(...)`-coercing them to the literal four-character string `'None'` -- which encodes nonsense. It should treat a `None` username/password as the empty bytes value `b''` instead. Concretely: `(None, 'pw')` should yield `'Basic OnB3'` and `(None, None)` should yield `'Basic Og=='`. The existing deprecation-warning path for non-`None`, non-string inputs (e.g. an integer) must be preserved.

The attached PR touches both files in one go.
</pr_description>

<pr_code>
--- a/src/requests/_internal_utils.py
+++ b/src/requests/_internal_utils.py
@@ -4,8 +4,9 @@
     necessary. This assumes ASCII unless told otherwise.
     """
     if isinstance(string, builtin_str):
-        out = string
-    else:
-        out = string.decode(encoding)
-
-    return out
+        return string
+    if isinstance(string, (bytes, bytearray)):
+        return bytes(string).decode(encoding)
+    raise TypeError(
+        f"to_native_string expected str or bytes, got {type(string).__name__}"
+    )
--- a/src/requests/auth.py
+++ b/src/requests/auth.py
@@ -1,4 +1,6 @@
-    if not isinstance(username, basestring):
+    if username is None:
+        username = b""
+    elif not isinstance(username, basestring):
         warnings.warn(
             "Non-string usernames will no longer be supported in Requests "
             f"3.0.0. Please convert the object you've passed in ({username!r}) to "
@@ -8,7 +10,9 @@
         )
         username = str(username)
 
-    if not isinstance(password, basestring):
+    if password is None:
+        password = b""
+    elif not isinstance(password, basestring):
         warnings.warn(
             "Non-string passwords will no longer be supported in Requests "
             f"3.0.0. Please convert the object you've passed in ({type(password)!r}) to "
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

Mechanical proof that label = `YES` is correct: apply the reference_edit patch from source #53 on top of the pinned baseline, then run `exec_assert` against the source's truth table. The label must match the outcome:

- `label=YES` -> exec_assert PASSES (all asserts in source.asserts evaluate True)
- `label=NO` -> exec_assert FAILS at least one assert

Verified mechanically by `python3 data/scripts/audit_review.py --id 93` (Pass 1).

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

If the source manifest changes, re-run `data/scripts/regen_review.py` and `data/scripts/audit_review.py`.

## Lock-in hash

SHA-256 of `(source_manifest, source_id, variant, label, issue_text)` JSON-serialized with sorted keys. Drift in any of these fields changes the hash. Cross-referenced in [data/scripts/docs/v1_review_lock_in.md](../../scripts/docs/v1_review_lock_in.md).

`7caee40a225363cf5f4776cb2784f2773fd2c4368367c7aa16bbbfd81ae661d8`
