# Archetype 13 — `tool_restriction_rerouting` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), tool restrictions are enforced through three orthogonal channels — top-level system prompt, an `AGENTS.md` file at the project root, or a custom primary-agent persona at `.opencode/agent/<name>.md`. This archetype covers the full tool-restriction surface tested by the v1 benchmark: a normal coding/search/triage task is wrapped with a tool denial (or affirmative requirement), and the model must accomplish the task by **rerouting through a less-obvious tool** while honoring the restriction.

Common restriction shapes the model must learn:

- **`write` denied → create new file via `bash`** (`echo > file`, `cat > file <<EOF`) **or via `edit` in new-file mode** (empty `oldString`).
- **`grep` and/or `glob` denied → search via `bash`** (`rg`, `find`, `ls -R`, `grep -r`) **or via plain `read`** of suspected files.
- **`bash` denied → all operations via specialised tools** (no shell-out for verification, no `git` commands, no package-manager invocation).
- **Parent-agent file reading denied → delegate reads via `task`** to a subagent that itself uses `read`. The parent must NOT shortcut by reading directly even once.
- **`bash`-only mode → search/read/write all via `bash`** — `rg` for search, `cat` for read, `tee` / `>` for write — even though specialised tools would be more natural.
- **Subagent-required mode → parent must dispatch at least one `task` subagent** for every read/grep operation; specialised tools forbidden at the parent layer.

The user's task should be a **normal coding/search/triage task** that would naturally invite the forbidden tool; the agent prompt enforces the restriction in one of the three channels. The deliverable should be a tangible artifact (a written file, a structured response) so the model can't satisfice with a chat-style answer that sidesteps the restriction.

## Distribution targets (mirror v1 `tool_restriction` benchmark)

The v1 benchmark `tool_restriction` family (samples #201–#230) has the following distribution; the example mix below is sized to match it within rounding:

| axis | benchmark | this archetype (7 examples) |
|---|---|---|
| **channel** — `system_prompt` / `agents_md` / `persona` | 53% / 37% / 10% (16/11/3) | 57% / 29% / 14% (4/2/1) |
| **parent task shape** — localization / editing / review | 53% / 33% / 14% (16/10/4) | 43% / 43% / 14% (3/3/1) |
| **restriction shape coverage** | 7+ shapes | covers all 7 distinct shapes |

Generators sampling from this archetype should preserve roughly this distribution.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the full user prompt the model sees. For localization-shaped samples, must include the structured-artifact format spec (`file::QualifiedName` lines, lex order, trailing newline). For editing-shaped samples, must include the function name and behavior contract. For review-shaped samples, must include the embedded PR diff inside `<candidate_diff>` tags plus the strict YES/NO + `<review>` schema.
- `"agent_name"`: string — kebab-case name describing the restriction (e.g. `"no-write-locator"`, `"no-bash-editor"`, `"subagent-only-locator"`).
- `"agent_content"`: string — markdown with YAML frontmatter (`mode: primary`). Body explicitly enumerates allowed tools AND forbidden tools. For non-trivial restrictions, **suggests the rerouting path** the model should take.
- `"channel"`: string — exactly one of `"system_prompt"`, `"agents_md"`, `"persona"`. Indicates which delivery channel the restriction rides on (the harness uses this to install the restriction in the right place).
- `"pre_command"`: string — bash to materialize the project the task operates on.

## Examples (7)

### Example 1 (system_prompt + no_write + localization-shape)

```
question:

In this checkout, write `location.txt` at the repo root listing — one per line, in lexicographic order — every function under `src/` that imports from the deprecated `legacy_logger` module. Each line is `file_path::QualifiedName`:
- Module-level functions → bare name (e.g. `bootstrap`)
- Methods on a class → `ClassName.method`

End with a single trailing newline. List nothing else.

agent_name: no-write-locator

agent_content:

---
name: no-write-locator
mode: primary
description: Locator agent that may not use the write tool. New files are created via bash or edit.
---
You may use these tools: read, grep, glob, bash, edit, task.

You may NOT use the write tool. If you need to create a new file, do one of:
- `bash` with `echo "..." > path` or `cat > path <<EOF ... EOF`.
- `edit` with an empty `oldString` and the desired content as `newString` (this creates the file).

This restriction applies for the entire session.

channel: system_prompt

pre_command:

mkdir -p src/handlers src/utils && cat > src/handlers/login.py << 'EOF'
from legacy_logger import log
def login(u):
    log('login', u)
    return True
EOF
cat > src/handlers/billing.py << 'EOF'
from new_logger import log
def bill(u, amt):
    log.info('bill', user=u, amount=amt)
    return True
EOF
cat > src/utils/format.py << 'EOF'
from legacy_logger import log
class Formatter:
    def fmt(self, x):
        log('fmt', x)
        return str(x)
EOF
cat > src/utils/cache.py << 'EOF'
class Cache:
    def __init__(self): self.m = {}
    def get(self, k): return self.m.get(k)
EOF
```

### Example 2 (agents_md + no_bash + editing-shape)

```
question:

In `lib/pricing.py`, change the `calculate_discount` function so it rejects negative input amounts: when `amount < 0`, raise `ValueError("amount must be non-negative")` before performing any computation. Preserve the existing behavior for `amount >= 0`.

agent_name: no-bash-editor

agent_content:

---
name: no-bash-editor
mode: primary
description: Editing agent that uses specialised file tools but never the shell.
---
You may use: read, write, edit, glob, grep, task.

You may NOT use the bash tool. No shell commands, no `npm`, no `python`, no `git`, no `pytest`. If verification is needed (e.g. confirming a substitution landed correctly), do it by reading the file you just edited.

channel: agents_md

pre_command:

mkdir -p lib && cat > lib/pricing.py << 'EOF'
def calculate_discount(amount, tier):
    rate = {"bronze": 0.05, "silver": 0.10, "gold": 0.15}.get(tier, 0.0)
    return amount * (1 - rate)
EOF
```

### Example 3 (agents_md + no_grep_no_glob + localization-shape)

```
question:

There's a config value called `RETRY_BACKOFF_MS` referenced across this microservice. Find every file under `services/` that defines or uses it, then write `backoff_audit.md` at the repo root with one line per file, in lex order, formatted as `path: <define|use>` (e.g. `services/api/client.py: use`). End with a single trailing newline.

agent_name: no-grep-no-glob

agent_content:

---
name: no-grep-no-glob
mode: primary
description: Search agent that may not use grep or glob; must use bash for cross-file search.
---
You may use: read, write, edit, bash, task.

You may NOT use grep or glob. When you need to search across files, use the bash tool with `rg` (ripgrep), `grep -r`, or `find`. The shell can do everything those two tools can.

If you only need to inspect a small number of named files, use read directly.

channel: agents_md

pre_command:

mkdir -p config services/api services/worker && cat > config/defaults.py << 'EOF'
RETRY_BACKOFF_MS = 250
MAX_RETRIES = 3
EOF
cat > services/api/client.py << 'EOF'
from config.defaults import RETRY_BACKOFF_MS
import time
def call_with_retry(fn):
    for i in range(3):
        try: return fn()
        except: time.sleep(RETRY_BACKOFF_MS / 1000.0)
EOF
cat > services/worker/queue.py << 'EOF'
from config.defaults import RETRY_BACKOFF_MS
def backoff_for(attempt): return RETRY_BACKOFF_MS * (2 ** attempt)
EOF
cat > services/worker/heartbeat.py << 'EOF'
import time
def heartbeat(): time.sleep(1.0)
EOF
```

### Example 4 (system_prompt + subagent_required + localization-shape)

```
question:

In this checkout, write `location.txt` at the repo root listing — one per line, in lexicographic order — every function in `pkg/handlers/` that calls `publish_event()`. Each line is `file_path::QualifiedName`:
- Module-level functions → bare name
- Methods on a class → `ClassName.method`
- Nested closure inside another function → `outer.inner`

End with a single trailing newline.

agent_name: subagent-only-locator

agent_content:

---
name: subagent-only-locator
mode: primary
description: Coordinator that never reads files directly; all reads go through a subagent.
---
You may use: bash (for `git`, build, lint only), edit, write, task.

You may NOT use read, grep, or glob directly. Whenever you need to inspect a file, dispatch a subagent via the task tool (e.g. `task(subagent_type="explore", prompt="read pkg/handlers/orders.go and report ...")`) and rely on the subagent's returned summary.

This applies to ALL file inspection — including the very first lookup. Never shortcut by reading once "to get oriented".

channel: system_prompt

pre_command:

mkdir -p pkg/handlers && cat > pkg/handlers/orders.go << 'EOF'
package handlers

func CreateOrder(orderID string) error {
    publish_event("order.created", orderID)
    return nil
}

func CancelOrder(orderID string) error {
    publish_event("order.cancelled", orderID)
    return nil
}

func RefundOrder(orderID string) error {
    return nil
}
EOF
cat > pkg/handlers/users.go << 'EOF'
package handlers

type UserService struct{}

func (s *UserService) Register(email string) error {
    publish_event("user.registered", email)
    return nil
}

func (s *UserService) Deactivate(email string) error {
    return nil
}
EOF
cat > pkg/handlers/events.go << 'EOF'
package handlers

func publish_event(name string, payload interface{}) error { return nil }
EOF
cat > go.mod << 'EOF'
module example.com/h
go 1.21
EOF
```

### Example 5 (persona + bash_only + editing-shape)

```
question:

Add a function `format_bytes(n int64) string` to `internal/util/util.go` that turns a byte count into a human-readable string ("1.5 MB", "723 B"). Round to one decimal for KB and above; bytes get no suffix decimal.

agent_name: bash-only-editor

agent_content:

---
name: bash-only-editor
mode: primary
description: Strict bash-only editor. All operations go through the shell.
---
You may ONLY use the bash tool. Do NOT use read, write, edit, grep, glob, or task.

For each operation, use the appropriate shell command:
- Read a file: `cat path`, `head path`, `sed -n '10,30p' path`.
- Search: `rg pattern path/`, `grep -rn pattern path/`.
- Edit: `sed -i 's/old/new/' path`, or full-file rewrite with `cat > path <<EOF ... EOF`.
- Create: `cat > path <<EOF ... EOF`.

This is enforced for the entire session. Pure single-tool fluency.

channel: persona

pre_command:

mkdir -p internal/util && cat > internal/util/util.go << 'EOF'
package util

func Sum(xs []int) int {
    total := 0
    for _, x := range xs {
        total += x
    }
    return total
}
EOF
cat > go.mod << 'EOF'
module example.com/proj
go 1.22
EOF
```

### Example 6 (system_prompt + parent_no_read + review-shape)

```
question:

A reviewer needs your judgment on whether the following pull request correctly fixes the described issue.

Repository: this checkout. The diff is shown below; you may delegate file inspection to a subagent if you need additional context, but you must not modify or execute code.

<pr_description>
The `RateLimiter.allow()` method in `service/limit.py` lets the first request through unconditionally, even when the configured `per_second` rate is 0. The fix should make `allow()` return False when `per_second <= 0`.
</pr_description>

<candidate_diff>
--- a/service/limit.py
+++ b/service/limit.py
@@ -7,8 +7,10 @@ class RateLimiter:
     def __init__(self, per_second: int):
         self.per_second = per_second
         self.tokens = per_second
         self.last = 0.0

     def allow(self) -> bool:
+        if self.per_second <= 0:
+            return False
         self.tokens -= 1
         return self.tokens >= 0
</candidate_diff>

Output schema (strict):
- A `<review>...</review>` block containing your reasoning.
- After `</review>`, on its own line, output exactly `YES` if the PR correctly addresses the issue, or `NO` if it does not. No other tokens.

agent_name: subagent-only-reviewer

agent_content:

---
name: subagent-only-reviewer
mode: primary
description: PR reviewer that may not read directly; all source inspection goes through a subagent.
---
You are a PR reviewer in a delegation-only posture. You may use: task, write (only for the final response), edit (forbidden — this is a read-only review).

You may NOT use read, grep, or glob, or bash. To inspect any file beyond what's already in the user prompt's diff, dispatch a subagent via task (e.g. `task(subagent_type="explore", prompt="...")`) and synthesise its summary.

Output the YES/NO + `<review>` schema requested by the user.

channel: system_prompt

pre_command:

git init -q . && mkdir -p service && cat > service/limit.py << 'EOF'
import time

class RateLimiter:
    def __init__(self, per_second: int):
        self.per_second = per_second
        self.tokens = per_second
        self.last = 0.0

    def allow(self) -> bool:
        self.tokens -= 1
        return self.tokens >= 0
EOF
git add -A && git -c user.email=d@e -c user.name=d commit -q -m initial
```

### Example 7 (system_prompt + no_glob + editing-shape)

```
question:

In `lib/config.py`, add a `Final` type annotation to every module-level constant (the constants that are defined with an uppercase name and no surrounding type annotation). Use `from typing import Final` and the syntax `NAME: Final = value`. Do not change any values.

agent_name: no-glob-typer

agent_content:

---
name: no-glob-typer
mode: primary
description: Editing agent that may not use glob; must read the named file directly.
---
You may use: read, write, edit, grep, bash, task.

You may NOT use the glob tool. The user prompt names the file you need to edit (`lib/config.py`); read it directly. Do not enumerate the directory.

channel: system_prompt

pre_command:

mkdir -p lib && cat > lib/config.py << 'EOF'
TIMEOUT_SEC = 30
MAX_RETRIES = 5
RETRY_BACKOFF_MS = 250
POOL_SIZE = 16
DEBUG_MODE = False

def get_pool_size() -> int:
    return POOL_SIZE
EOF
```

## Notes on the schema

- **Channel `system_prompt`** is the most common in the benchmark (53%) and this archetype mirrors that — 4 of 7 examples use it. A generator producing samples should default to `system_prompt` unless the scenario specifically benefits from `AGENTS.md` (project-specific conventions) or `persona` (custom-agent identity).
- **Parent task shape variety** matters: tool_restriction is layered on top of localization / editing / review tasks in the benchmark, so the archetype includes one example of each shape combined with a restriction. The localization examples (#1, #3, #4) carry the strict `file::QualifiedName` artifact format; the editing examples (#2, #5, #7) carry behavior contracts; the review example (#6) carries the YES/NO + `<review>` schema from archetype 12.
- **Restriction shape coverage** spans no_write (Ex 1), no_bash (Ex 2), no_grep_no_glob (Ex 3), subagent_required (Ex 4), bash_only (Ex 5), parent_no_read (Ex 6), no_glob (Ex 7) — 7 distinct shapes covering every kind tested in the benchmark.

## Overlap notes

All seven examples use synthetic projects and synthetic identifiers:
- `legacy_logger` import audit on synthetic Python services (Ex 1)
- `calculate_discount` in synthetic `lib/pricing.py` (Ex 2)
- `RETRY_BACKOFF_MS` audit on synthetic microservice (Ex 3)
- `publish_event` callers in synthetic Go `pkg/handlers/` (Ex 4)
- `Sum` / `format_bytes` in synthetic Go `internal/util/` (Ex 5)
- `RateLimiter.allow` in synthetic Python `service/limit.py` (Ex 6)
- `lib/config.py` constants in a synthetic Python config file (Ex 7)

None of these match v1 benchmark function names, file paths, or skill names. The benchmark's `tool_restriction` samples target callers of `merge_cookies`, `Session.prepare_request`, `RequestsCookieJar.update`, `iter_slices`, `unquote_header_value`, etc. — all explicitly avoided here.

The seven examples deliberately span all three injection channels (`system_prompt`, `agents_md`, `persona`) in a 4/2/1 ratio that mirrors the benchmark's 16/11/3 distribution. They also span localization, editing, and review parent shapes (3/3/1) so the trained model learns that tool restrictions compose with each underlying task type.
