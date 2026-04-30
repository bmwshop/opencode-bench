# Archetype 12 — `pr_review_judgment` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), some workflows require the assistant to **judge a candidate change** rather than make one — review a proposed pull request, decide whether it correctly addresses the described issue, and emit a structured verdict. The assistant operates in a read-only posture (no edits, no shell mutations) and produces output in a fixed schema so a downstream grader / CI step can parse it.

Common review-judgment shapes:

- **Bug-fix verification** — "issue X is described; this PR claims to fix it; does it actually?"
- **Regression detection** — "this PR adds a new feature; does it break any documented behavior?"
- **Style / convention compliance** — "this PR adds new code; does it follow the project's conventions?"
- **Security review** — "this PR touches auth/crypto; does it introduce a vulnerability?"
- **Spec compliance** — "the spec says X; does this PR conform?"

The output schema is **strict**: a non-empty `<review>...</review>` block containing the reasoning, followed by a final judgment line consisting of exactly the literal token `YES` or `NO` (uppercase, no punctuation). The assistant operates in a *read-only* posture: it may freely use any inspection tool (`read`, `grep`, `glob`) and may delegate to a subagent via `task` if helpful, but must NOT call the three mutation tools (`edit`, `write`, `bash`). Both `YES` and `NO` outcomes are common and the training mix should be roughly balanced.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the user's review request, presented as a triage / judgment task.
- `"pr_diff"`: string — the candidate diff, in unified-diff format (`--- a/...` / `+++ b/...` / `@@ ... @@`).
- `"issue_description"`: string — the problem the PR claims to address (used to ground "YES" cases) or the spec the PR claims to implement.
- `"correct_verdict"`: string — exactly `"YES"` or `"NO"`. The expected answer.
- `"agent_prompt"`: string — content for `AGENTS.md` or system prompt that establishes read-only judgment posture and the exact output schema (`<review>` block + literal `YES`/`NO`).
- `"pre_command"`: string — bash to materialize the codebase the PR applies against; the diff must apply cleanly to this state.

## Examples (4)

### Example 1 (verdict: YES — bug fix correctly addresses the issue)

```
question: A reviewer needs your judgment on whether this pull request correctly fixes the described issue. Repository: this checkout. You may read any file under lib/ to verify, but you must not modify or execute code.

issue_description:

The clamp_to_range helper in lib/numeric.py is supposed to clamp a value into a [lo, hi] range, but when lo > hi it returns the bare input unchanged instead of raising. The fix should make the helper raise a ValueError if the caller passes lo > hi.

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

correct_verdict: YES

agent_prompt:

You are a code reviewer in plan mode. You may use any read-only tool (read, grep, glob, and task to delegate to a subagent if helpful), but you may not call edit, write, or bash — no mutations and no shell execution. Your job is to judge whether the candidate PR correctly addresses the issue described.

Output schema (strict):

1. A `<review>...</review>` block containing your reasoning. Cite specific file:line references from the diff or the original code. Be concise but specific.
2. After `</review>`, on its own line, output exactly `YES` if the PR correctly addresses the issue, or `NO` if it does not. No other tokens, no punctuation, no markdown.

Do not output anything before `<review>` or after the final `YES`/`NO`.

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
question: Review this proposed fix and decide whether it lands. Don't apply changes; just give me your judgment.

issue_description:

The find_user_by_email function in service/lookup.py is case-sensitive: searching for "alice@example.com" misses users stored as "Alice@example.com". The fix must make the email comparison case-insensitive on the lookup path.

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

correct_verdict: NO

agent_prompt:

You are a code reviewer in plan mode. You may use any read-only tool (read, grep, glob, task), but you may not call edit, write, or bash — no mutations and no shell execution.

Output schema (strict):

- A `<review>...</review>` block with your reasoning, citing file:line where useful.
- On its own line after `</review>`: exactly `YES` if the PR correctly addresses the issue, or `NO` if it does not.

Do not produce any other tokens.

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
question: We have a security report that says the order-lookup endpoint is vulnerable to IDOR. Engineering pushed a fix; tell me if it actually closes the hole.

issue_description:

GET /orders/<id> in api/views.py returns the order regardless of which user requests it, allowing one user to view any other user's orders by guessing IDs (Insecure Direct Object Reference). The fix must enforce that the requesting user owns the order.

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

correct_verdict: YES

agent_prompt:

You review pull requests in plan mode. Read-only inspection only — read, grep, glob, and task are all available; never call edit, write, or bash.

Output schema:
- `<review>` block: reasoning + file:line citations.
- After `</review>`: exactly `YES` or `NO` on its own line.

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
question: This PR claims to fix the timezone bug in stamp_iso but I'm not sure. Take a read-only look and give me YES if it's a clean fix, NO if it isn't.

issue_description:

stamp_iso in lib/stamps.go currently returns timestamps in the server's local timezone, which causes inconsistent output across deployments. The function should always return UTC. The fix must not break the existing behavior of accepting both time.Time and *time.Time inputs.

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

correct_verdict: NO

agent_prompt:

You are a read-only PR reviewer. Tools allowed: read, grep, glob, task. Tools forbidden: edit, write, bash. (Mutations and shell execution only — read-only inspection and subagent delegation are fine.)

Output: a `<review>` block followed by a single line containing exactly `YES` or `NO`. Nothing else.

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

## Overlap notes

All four examples use synthetic projects with synthetic function names (`clamp_to_range`, `find_user_by_email` in `UserStore`, `get_order_view`, `StampISO`). None match v1 benchmark function names (`iter_slices`, `unquote_header_value`, `dispatch_hook`, `address_in_network`, etc.) and none replicate the `psf/requests` / `encode/httpx` / `pallets/click` / `karpathy/autoresearch` benchmark scenarios.

The benchmark's `code_review` family (samples #91-#100) reviews PRs against `iter_slices`, `unquote_header_value`, `to_native_string`, `parse_header_links`, `morsel_to_cookie`, `extract_cookies_to_jar`, `atomic_open`, `cookiejar_from_dict`, `RequestHooksMixin`, `RequestsCookieJar.update` — all explicitly avoided here. The four examples target different scenarios entirely (a numeric clamp helper, an in-memory user store, a Django IDOR fix, a Go timestamp formatter).
