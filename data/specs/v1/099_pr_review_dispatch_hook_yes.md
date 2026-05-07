# v1 #99 pr_review_dispatch_hook_yes

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
- source_id: **#59** (edit_dispatch_hook_skip_none_with_caller)
- variant: **reference_edit**
- gold label: **YES**

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> Issue (cross-cutting): two related hook-system holes.
> 
> 1. The dispatcher in the tiny `hooks` module crashes when the registered callback list contains a `None` entry, because it calls `None(...)` which raises `TypeError: 'NoneType' object is not callable`. It should silently skip `None` entries while still invoking valid callbacks.
> 
> Concretely: with `hook_data=10` and the callback list `[None, lambda d: d + 1]`, the dispatcher must now return `11`. With `[None]` it must return `10` (the original data, unchanged). All existing behaviour is preserved (no hooks -> data unchanged; non-list single-callable hook value still invoked; chained callbacks still propagate).
> 
> 2. The sibling sessions module needs a NEW top-level helper `apply_response_hooks(hooks, response)` that defends against malformed `hooks` arguments before delegating to the dispatcher. It must return `response` unchanged when `hooks` is `None`, when `hooks` is not a `dict`, or when `hooks` is a dict that doesn't contain the key `'response'`. Otherwise it delegates to the lower-level dispatcher with the event key `'response'`.
> 
> The attached PR touches both files together.

## PR under review (in prompt as `<pr_code>`)

Unified diff constructed from the source manifest's `reference_edit` for source #59, against pin `79f4df84cf77`:

```diff
--- a/src/requests/hooks.py
+++ b/src/requests/hooks.py
@@ -6,6 +6,8 @@
         if hasattr(hooks, "__call__"):
             hooks = [hooks]
         for hook in hooks:
+            if hook is None:
+                continue
             _hook_data = hook(hook_data, **kwargs)
             if _hook_data is not None:
                 hook_data = _hook_data
--- a/src/requests/sessions.py
+++ b/src/requests/sessions.py
@@ -1,4 +1,20 @@
     return merge_setting(request_hooks, session_hooks, dict_class)
 
 
+def apply_response_hooks(hooks, response):
+    """Defensive wrapper for invoking the 'response' hook chain.
+
+    Returns ``response`` unchanged when ``hooks`` is None, when ``hooks``
+    is not a dict, or when the dict has no ``'response'`` key. Otherwise
+    delegates to :func:`dispatch_hook` with the ``'response'`` event.
+    """
+    if hooks is None:
+        return response
+    if not isinstance(hooks, dict):
+        return response
+    if "response" not in hooks:
+        return response
+    return dispatch_hook("response", hooks, response)
+
+
 class SessionRedirectMixin:
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
Issue (cross-cutting): two related hook-system holes.

1. The dispatcher in the tiny `hooks` module crashes when the registered callback list contains a `None` entry, because it calls `None(...)` which raises `TypeError: 'NoneType' object is not callable`. It should silently skip `None` entries while still invoking valid callbacks.

Concretely: with `hook_data=10` and the callback list `[None, lambda d: d + 1]`, the dispatcher must now return `11`. With `[None]` it must return `10` (the original data, unchanged). All existing behaviour is preserved (no hooks -> data unchanged; non-list single-callable hook value still invoked; chained callbacks still propagate).

2. The sibling sessions module needs a NEW top-level helper `apply_response_hooks(hooks, response)` that defends against malformed `hooks` arguments before delegating to the dispatcher. It must return `response` unchanged when `hooks` is `None`, when `hooks` is not a `dict`, or when `hooks` is a dict that doesn't contain the key `'response'`. Otherwise it delegates to the lower-level dispatcher with the event key `'response'`.

The attached PR touches both files together.
</pr_description>

<pr_code>
--- a/src/requests/hooks.py
+++ b/src/requests/hooks.py
@@ -6,6 +6,8 @@
         if hasattr(hooks, "__call__"):
             hooks = [hooks]
         for hook in hooks:
+            if hook is None:
+                continue
             _hook_data = hook(hook_data, **kwargs)
             if _hook_data is not None:
                 hook_data = _hook_data
--- a/src/requests/sessions.py
+++ b/src/requests/sessions.py
@@ -1,4 +1,20 @@
     return merge_setting(request_hooks, session_hooks, dict_class)
 
 
+def apply_response_hooks(hooks, response):
+    """Defensive wrapper for invoking the 'response' hook chain.
+
+    Returns ``response`` unchanged when ``hooks`` is None, when ``hooks``
+    is not a dict, or when the dict has no ``'response'`` key. Otherwise
+    delegates to :func:`dispatch_hook` with the ``'response'`` event.
+    """
+    if hooks is None:
+        return response
+    if not isinstance(hooks, dict):
+        return response
+    if "response" not in hooks:
+        return response
+    return dispatch_hook("response", hooks, response)
+
+
 class SessionRedirectMixin:
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

Mechanical proof that label = `YES` is correct: apply the reference_edit patch from source #59 on top of the pinned baseline, then run `exec_assert` against the source's truth table. The label must match the outcome:

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

`c1f9f234d799fa5e7231d00ce313bd9487540ce2da41e6482461c231632a496b`
