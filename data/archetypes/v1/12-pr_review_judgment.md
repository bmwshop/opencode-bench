# Archetype 12 — `pr_review_judgment` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), some workflows require the assistant to **judge a candidate change** rather than make one — review a proposed pull request, decide whether it correctly addresses the described issue, and emit a structured verdict.

PR-judgment samples are executed in OpenCode's built-in **plan mode** (see archetype 06 [`plan_mode`](06-plan_mode.md)). The harness boots the run with `--agent plan`; OpenCode auto-injects a system reminder forbidding any file modification and any non-readonly shell command. The model sees this reminder before the user prompt — that's the *primary* read-only enforcement. The user prompt itself only needs to (a) describe the review task, (b) embed the PR diff and issue description, and (c) specify the strict output schema.

Common review-judgment shapes:

- **Bug-fix verification** — "issue X is described; this PR claims to fix it; does it actually?"
- **Regression detection** — "this PR adds a new feature; does it break any documented behavior?"
- **Style / convention compliance** — "this PR adds new code; does it follow the project's conventions?"
- **Security review** — "this PR touches auth/crypto; does it introduce a vulnerability?"
- **Spec compliance** — "the spec says X; does this PR conform?"

The output schema is **strict**: a non-empty `<review>...</review>` block containing the reasoning, followed by a final judgment line consisting of exactly the literal token `YES` or `NO` (uppercase, no punctuation). The benchmark grader checks two things from the trace: (i) the response contains the `<review>...</review>` block and the literal `YES`/`NO` token, and (ii) the trace contains no `edit`, `write`, or `bash` calls. Both `YES` and `NO` outcomes are common; the training mix should be roughly balanced.

PR review naturally fits in one assistant turn — subagent dispatch via `task` is unnecessary and observed to be unused in the benchmark traces (claude: 0 `task` calls across 30 PR-review trials).

### Three-layer enforcement (for reference)

| layer | mechanism | who enforces |
|---|---|---|
| 1. Plan mode | `agent_mode: "plan"` → harness boots OpenCode in plan mode → auto-injected reminder | OpenCode harness (primary) |
| 2. User-prompt language | "you may read any file under `<scope>` but you must not modify or execute code" — embedded in `question` | the model (soft, belt-and-suspenders) |
| 3. Grader check | `no_tool_name not_equals: [edit, write, bash]` against the trace | post-hoc evaluator |

The archetype focuses on layers 1 and 2; layer 3 is a property of the eval harness and not generator-controllable.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the full user prompt the model sees. It must contain: a one-paragraph task description, repo/scope context, the issue inside `<pr_description>...</pr_description>` tags, the candidate diff inside `<candidate_diff>...</candidate_diff>` tags, and an explicit *output schema* section that pins the `<review>...</review>` block + literal `YES`/`NO` requirement. A short "you may read but not modify" sentence is fine as belt-and-suspenders to plan mode but not required.
- `"agent_mode"`: string — exactly `"plan"`. Signals the harness to invoke OpenCode's plan mode for this run.
- `"pr_diff"`: string — the candidate diff in unified-diff format (`--- a/...` / `+++ b/...` / `@@ ... @@`). Helper field; should be the same diff as the one embedded in `question`'s `<candidate_diff>` tags. The pipeline may use this for templating/validation.
- `"issue_description"`: string — the problem the PR claims to address. Helper field; should match the text inside `question`'s `<pr_description>` tags.
- `"correct_verdict"`: string — exactly `"YES"` or `"NO"`. The expected answer; used by the grader's `text_contains` check.
- `"pre_command"`: string — bash to materialize the codebase the PR applies against; the diff in `pr_diff` must apply cleanly to this initial state.

## Examples (4)

### Example 1 (verdict: YES — bug fix correctly addresses the issue)

```
question:

A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this checkout. You may read any file under `lib/` to verify your judgment, but you must not modify or execute code.

<pr_description>
The `clamp_to_range` helper in `lib/numeric.py` is supposed to clamp a value into a [lo, hi] range, but when lo > hi it returns the bare input unchanged instead of raising. The fix should make the helper raise a ValueError if the caller passes lo > hi.
</pr_description>

<candidate_diff>
--- a/lib/numeric.py
+++ b/lib/numeric.py
@@ -3,6 +3,8 @@ def clamp_to_range(value, lo, hi):
     """Clamp value into the [lo, hi] interval."""
+    if lo > hi:
+        raise ValueError(f"clamp_to_range: lo ({lo}) > hi ({hi})")
     if value < lo:
         return lo
     if value > hi:
         return hi
     return value
</candidate_diff>

Output schema (strict):

1. A `<review>...</review>` block containing your reasoning. Cite specific file:line references from the diff or the original code. Be concise but specific.
2. After `</review>`, on its own line, output exactly `YES` if the PR correctly addresses the issue, or `NO` if it does not. No other tokens, no punctuation, no markdown.

Do not output anything before `<review>` or after the final `YES`/`NO`.

agent_mode: plan

pr_diff:

--- a/lib/numeric.py
+++ b/lib/numeric.py
@@ -3,6 +3,8 @@ def clamp_to_range(value, lo, hi):
     """Clamp value into the [lo, hi] interval."""
+    if lo > hi:
+        raise ValueError(f"clamp_to_range: lo ({lo}) > hi ({hi})")
     if value < lo:
         return lo
     if value > hi:
         return hi
     return value

issue_description:

The clamp_to_range helper in lib/numeric.py is supposed to clamp a value into a [lo, hi] range, but when lo > hi it returns the bare input unchanged instead of raising. The fix should make the helper raise a ValueError if the caller passes lo > hi.

correct_verdict: YES

pre_command:

git init -q . && mkdir -p lib && cat > lib/numeric.py << 'EOF'
def clamp_to_range(value, lo, hi):
    """Clamp value into the [lo, hi] interval."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
EOF
git add -A && git -c user.email=d@e -c user.name=d commit -q -m initial
```

### Example 2 (verdict: NO — fix is in the wrong place)

```
question:

Review this proposed fix and decide whether it lands. Don't apply changes; just give me your judgment.

Repository: this checkout. You may read any file under `service/` to verify, but you must not modify or execute code.

<pr_description>
The `find_user_by_email` function in `service/lookup.py` is case-sensitive: searching for "alice@example.com" misses users stored as "Alice@example.com". The fix must make the email comparison case-insensitive on the lookup path.
</pr_description>

<candidate_diff>
--- a/service/lookup.py
+++ b/service/lookup.py
@@ -8,8 +8,9 @@ class UserStore:
     def find_user_by_email(self, email: str):
         for u in self._users:
             if u.email == email:
                 return u
         return None

-    def add_user(self, name: str, email: str) -> None:
+    def add_user(self, name: str, email: str) -> None:
+        email = email.lower()
         self._users.append(User(name=name, email=email))
</candidate_diff>

Output schema (strict):

- A `<review>...</review>` block with your reasoning, citing file:line where useful.
- On its own line after `</review>`: exactly `YES` if the PR correctly addresses the issue, or `NO` if it does not.

Do not produce any other tokens.

agent_mode: plan

pr_diff:

--- a/service/lookup.py
+++ b/service/lookup.py
@@ -8,8 +8,9 @@ class UserStore:
     def find_user_by_email(self, email: str):
         for u in self._users:
             if u.email == email:
                 return u
         return None

-    def add_user(self, name: str, email: str) -> None:
+    def add_user(self, name: str, email: str) -> None:
+        email = email.lower()
         self._users.append(User(name=name, email=email))

issue_description:

The find_user_by_email function in service/lookup.py is case-sensitive: searching for "alice@example.com" misses users stored as "Alice@example.com". The fix must make the email comparison case-insensitive on the lookup path.

correct_verdict: NO

pre_command:

git init -q . && mkdir -p service && cat > service/lookup.py << 'EOF'
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

class UserStore:
    def __init__(self):
        self._users = []
    def find_user_by_email(self, email: str):
        for u in self._users:
            if u.email == email:
                return u
        return None
    def add_user(self, name: str, email: str) -> None:
        self._users.append(User(name=name, email=email))
EOF
git add -A && git -c user.email=d@e -c user.name=d commit -q -m initial
```

### Example 3 (verdict: YES — security IDOR fix)

```
question:

We have a security report that says the order-lookup endpoint is vulnerable to IDOR. Engineering pushed a fix; tell me if it actually closes the hole.

Repository: this checkout. You may read any file under `api/` to verify, but you must not modify or execute code.

<pr_description>
GET /orders/<id> in api/views.py returns the order regardless of which user requests it, allowing one user to view any other user's orders by guessing IDs (Insecure Direct Object Reference). The fix must enforce that the requesting user owns the order.
</pr_description>

<candidate_diff>
--- a/api/views.py
+++ b/api/views.py
@@ -10,8 +10,13 @@ from .models import Order
 from django.http import JsonResponse, Http404

 def get_order_view(request, order_id):
     o = Order.objects.filter(id=order_id).first()
     if not o:
         raise Http404
+    if o.user_id != request.user.id:
+        raise Http404
     return JsonResponse({'id': o.id, 'total': o.total_cents})
</candidate_diff>

Output schema:
- `<review>` block: reasoning + file:line citations.
- After `</review>`: exactly `YES` or `NO` on its own line. Nothing else.

agent_mode: plan

pr_diff:

--- a/api/views.py
+++ b/api/views.py
@@ -10,8 +10,13 @@ from .models import Order
 from django.http import JsonResponse, Http404

 def get_order_view(request, order_id):
     o = Order.objects.filter(id=order_id).first()
     if not o:
         raise Http404
+    if o.user_id != request.user.id:
+        raise Http404
     return JsonResponse({'id': o.id, 'total': o.total_cents})

issue_description:

GET /orders/<id> in api/views.py returns the order regardless of which user requests it, allowing one user to view any other user's orders by guessing IDs (Insecure Direct Object Reference). The fix must enforce that the requesting user owns the order.

correct_verdict: YES

pre_command:

git init -q . && mkdir -p api && cat > api/views.py << 'EOF'
from django.http import JsonResponse, Http404
from .models import Order

def get_order_view(request, order_id):
    o = Order.objects.filter(id=order_id).first()
    if not o:
        raise Http404
    return JsonResponse({'id': o.id, 'total': o.total_cents})
EOF
cat > api/models.py << 'EOF'
from django.db import models
class Order(models.Model):
    user_id = models.IntegerField()
    total_cents = models.IntegerField()
EOF
git add -A && git -c user.email=d@e -c user.name=d commit -q -m initial
```

### Example 4 (verdict: NO — fix introduces a regression)

```
question:

This PR claims to fix the timezone bug in `StampISO` but I'm not sure. Take a read-only look and give me YES if it's a clean fix, NO if it isn't.

Repository: this checkout. You may read any file under `lib/` to verify, but you must not modify or execute code.

<pr_description>
StampISO in lib/stamps.go currently returns timestamps in the server's local timezone, which causes inconsistent output across deployments. The function should always return UTC. The fix must not break the existing behavior of accepting both time.Time and *time.Time inputs.
</pr_description>

<candidate_diff>
--- a/lib/stamps.go
+++ b/lib/stamps.go
@@ -7,11 +7,8 @@ import (
 	"time"
 )

-func StampISO(t interface{}) string {
-	switch v := t.(type) {
-	case time.Time:
-		return v.Format(time.RFC3339)
-	case *time.Time:
-		if v == nil { return "" }
-		return v.Format(time.RFC3339)
-	}
-	return ""
+func StampISO(t time.Time) string {
+	return t.UTC().Format(time.RFC3339)
 }
</candidate_diff>

Output: a `<review>` block followed by a single line containing exactly `YES` or `NO`. Nothing else.

agent_mode: plan

pr_diff:

--- a/lib/stamps.go
+++ b/lib/stamps.go
@@ -7,11 +7,8 @@ import (
 	"time"
 )

-func StampISO(t interface{}) string {
-	switch v := t.(type) {
-	case time.Time:
-		return v.Format(time.RFC3339)
-	case *time.Time:
-		if v == nil { return "" }
-		return v.Format(time.RFC3339)
-	}
-	return ""
+func StampISO(t time.Time) string {
+	return t.UTC().Format(time.RFC3339)
 }

issue_description:

StampISO in lib/stamps.go currently returns timestamps in the server's local timezone, which causes inconsistent output across deployments. The function should always return UTC. The fix must not break the existing behavior of accepting both time.Time and *time.Time inputs.

correct_verdict: NO

pre_command:

git init -q . && mkdir -p lib && cat > lib/stamps.go << 'EOF'
package lib

import (
	"time"
)

func StampISO(t interface{}) string {
	switch v := t.(type) {
	case time.Time:
		return v.Format(time.RFC3339)
	case *time.Time:
		if v == nil { return "" }
		return v.Format(time.RFC3339)
	}
	return ""
}
EOF
cat > go.mod << 'EOF'
module example.com/x
go 1.21
EOF
git add -A && git -c user.email=d@e -c user.name=d commit -q -m initial
```

## Notes on the schema

- **No `agent_prompt` field.** Earlier drafts of this archetype included an `agent_prompt` field that mixed up two things: the read-only tool restriction and the output-schema spec. The benchmark itself doesn't use a separate channel for these — the read-only restriction comes from plan mode (`agent_mode: "plan"` → harness reminder), and the output-schema spec lives directly in the `question` text. The new schema reflects that: one prompt the model sees, one mode signal to the harness, two helper fields (`pr_diff`, `issue_description`) for the generator pipeline.
- **Plan mode interplay with archetype 06.** Archetype 06 (`plan_mode`) describes generic plan-mode usage (refactor plans, dependency-upgrade plans, etc.) where the deliverable is a written plan. Archetype 12 specialises that for *judgment* tasks where the deliverable is a strict YES/NO + `<review>` schema instead of a plan. Both archetypes share `agent_mode: "plan"` as the activation signal.
- **Why duplicate `pr_diff` / `issue_description` between `question` and helper fields.** The redundancy is intentional. The `question` shows the model exactly what it sees (with `<pr_description>` and `<candidate_diff>` tags). The helper fields let the generator pipeline interpolate them via a stable template, validate that the diff applies to `pre_command`'s initial state, and re-extract the gold answer if needed.

## Overlap notes

All four examples use synthetic projects with synthetic function names (`clamp_to_range`, `find_user_by_email` in `UserStore`, `get_order_view`, `StampISO`). None match v1 benchmark function names (`iter_slices`, `unquote_header_value`, `dispatch_hook`, `address_in_network`, etc.) and none replicate the `psf/requests` / `encode/httpx` / `pallets/click` / `karpathy/autoresearch` benchmark scenarios.

The benchmark's `review_judgment` family (samples #91-#100) reviews PRs against `iter_slices`, `unquote_header_value`, `to_native_string`, `parse_header_links`, `morsel_to_cookie`, `extract_cookies_to_jar`, `atomic_open`, `cookiejar_from_dict`, `RequestHooksMixin`, `RequestsCookieJar.update` — all explicitly avoided here. The four examples target different scenarios entirely (a numeric clamp helper, an in-memory user store, a Django IDOR fix, a Go timestamp formatter).
