# v1 #100 pr_review_address_in_network_no

## Category

review_judgment

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Issue (in prompt as `<pr_description>`)

The bug-tracker-voice issue the reviewer is asked to consider:

> Issue (cross-cutting): two related defensive holes that need to be fixed together.
> 
> 1. `address_in_network` in the requests utilities module today crashes with `OSError` or `ValueError` whenever the IP or CIDR string is malformed. It should return `False` cleanly instead. Concretely: `('not-an-ip', '192.168.1.0/24')` should return `False`; `('192.168.1.1', 'not-a-cidr')` should return `False`; `('192.168.1.1', '192.168.1.0/not-a-mask')` should return `False`. All existing behaviour on well-formed inputs is preserved (`('192.168.1.1', '192.168.1.0/24')` -> `True`; `('192.168.2.1', '192.168.1.0/24')` -> `False`; `('10.0.0.5', '10.0.0.0/8')` -> `True`).
> 
> 2. The sibling HTTP-adapter module needs a NEW top-level helper `_proxy_target_in_network(target_ip, cidr)` that prefilters obviously bad arguments (None or empty string for either) before delegating to the lower-level helper.
> 
> The attached PR claims to address both.

## PR under review (in prompt as `<pr_code>`)

Unified diff under review (against pin `79f4df84cf77`):

```diff
--- a/src/requests/adapters.py
+++ b/src/requests/adapters.py
@@ -4,4 +4,18 @@
 DEFAULT_POOL_TIMEOUT = None
 
 
+def _proxy_target_in_network(target_ip, cidr):
+    """Defensive wrapper for CIDR membership testing in proxy logic.
+
+    Returns ``False`` when either ``target_ip`` or ``cidr`` is ``None``
+    or an empty string, otherwise delegates to ``address_in_network``
+    (which is itself defensive against malformed IP / CIDR strings).
+    """
+    if target_ip is None or target_ip == "":
+        return False
+    if cidr is None or cidr == "":
+        return False
+    return address_in_network(target_ip, cidr)
+
+
 def _urllib3_request_context(
```

## Prompt

This is the LITERAL text the agent receives, byte-identical to the `prompt` field of this sample's row in [data/samples_v1.jsonl](../../samples_v1.jsonl):

```text
A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this `requests` checkout. You may read any file under `src/requests/` to verify your judgment, but you must not modify or execute code.

<pr_description>
Issue (cross-cutting): two related defensive holes that need to be fixed together.

1. `address_in_network` in the requests utilities module today crashes with `OSError` or `ValueError` whenever the IP or CIDR string is malformed. It should return `False` cleanly instead. Concretely: `('not-an-ip', '192.168.1.0/24')` should return `False`; `('192.168.1.1', 'not-a-cidr')` should return `False`; `('192.168.1.1', '192.168.1.0/not-a-mask')` should return `False`. All existing behaviour on well-formed inputs is preserved (`('192.168.1.1', '192.168.1.0/24')` -> `True`; `('192.168.2.1', '192.168.1.0/24')` -> `False`; `('10.0.0.5', '10.0.0.0/8')` -> `True`).

2. The sibling HTTP-adapter module needs a NEW top-level helper `_proxy_target_in_network(target_ip, cidr)` that prefilters obviously bad arguments (None or empty string for either) before delegating to the lower-level helper.

The attached PR claims to address both.
</pr_description>

<pr_code>
--- a/src/requests/adapters.py
+++ b/src/requests/adapters.py
@@ -4,4 +4,18 @@
 DEFAULT_POOL_TIMEOUT = None
 
 
+def _proxy_target_in_network(target_ip, cidr):
+    """Defensive wrapper for CIDR membership testing in proxy logic.
+
+    Returns ``False`` when either ``target_ip`` or ``cidr`` is ``None``
+    or an empty string, otherwise delegates to ``address_in_network``
+    (which is itself defensive against malformed IP / CIDR strings).
+    """
+    if target_ip is None or target_ip == "":
+        return False
+    if cidr is None or cidr == "":
+        return False
+    return address_in_network(target_ip, cidr)
+
+
 def _urllib3_request_context(
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
