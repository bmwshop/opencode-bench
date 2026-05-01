# Archetype 13 — `tool_restriction_rerouting` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), tool restrictions can be applied via three mechanisms; this archetype covers the **two soft (prompt-based) mechanisms**, where every tool remains visible in the model's schema and the restriction is enforced by *prompted compliance*:

- **`agents_md`** — an `AGENTS.md` file at the project root. OpenCode auto-discovers it at session start and **appends its content to the agent's system prompt**. The default agent stays active.
- **`custom_primary_agent`** — a primary-agent definition file at `.opencode/agents/<name>.md` with `mode: primary`. Activated by the run row's `agent: <name>` field. Its body **replaces** the default agent's system prompt entirely.

The third (hard) mechanism — `opencode.json` `permission` config — actually **removes** denied tools from the model's schema so the model literally can't see them. That mechanism is covered by **[archetype 11 (`tool_restriction_permissions`)](11-tool_restriction_permissions.md)** and is out of scope here.

In the v1 benchmark `tool_restriction` family (samples #201–#230), the soft channels split roughly 11 `agents_md` to 3 `custom_primary_agent` (78%/22% of the soft slice; the other 16 samples use the hard `opencode.json` mechanism). This archetype's example mix mirrors the soft-channel ratio.

The training signal is *creative compliance under restriction*: a normal coding/search/triage task is wrapped with a tool denial (or affirmative requirement), and the model must accomplish the task by **rerouting through a less-obvious tool** while honoring the restriction.

Common restriction shapes the model must learn:

- **`bash` denied → all operations via specialised tools** (no shell-out for verification, no `git` commands, no package-manager invocation).
- **`grep` and/or `glob` denied → search via `bash`** (`rg`, `find`, `ls -R`, `grep -r`) **or via plain `read`** of suspected files.
- **`bash`-only mode → search/read/write all via `bash`** — `rg` for search, `cat` for read, `tee` / `>` for write — even though specialised tools would be more natural.
- **Subagent-required mode → parent must dispatch at least one `task` subagent** for every read/grep operation; specialised tools forbidden at the parent layer.

### Restriction mechanism vs. restriction type — keep separate

Two distinct concepts that are easy to conflate:

- **Restriction *mechanism*** = where the restriction text physically lives. Two soft channels (covered here): `agents_md` and `custom_primary_agent`. Plus the hard `opencode.json` channel (covered by archetype 11).
- **Restriction *type*** = what the rule requires. Common types: `no_bash`, `no_grep_no_glob`, `bash_only`, `subagent_required`, etc. Some types (e.g. `subagent_required`) require the model to use the `task` tool to delegate, but **the subagent itself is not a restriction mechanism** — it's a tool the model is *required to use* when the restriction type calls for it.

A given restriction type can ride on any channel; the benchmark mixes them.

## Distribution targets (mirror v1 `tool_restriction` benchmark, soft-channel slice)

| axis | benchmark (soft slice only) | this archetype (4 examples) |
|---|---|---|
| **channel** — `agents_md` / `custom_primary_agent` | 78% / 22% (11/3) | 75% / 25% (3/1) |
| **parent task shape** — localization / editing / review | 53% / 33% / 14% (16/10/4) overall | 25% / 50% / 25% (1/2/1) |
| **restriction shape coverage** | 7+ shapes used | covers the 4 most common (~63% of benchmark samples) |

For the 53% of benchmark `tool_restriction` samples that use `opencode.json` permission gating (mutation kinds with `_system` suffix), see archetype 11.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the full user prompt the model sees. For localization-shaped samples, must include the structured-artifact format spec (`file::QualifiedName` lines, lex order, trailing newline). For editing-shaped samples, must include the function name and behavior contract. For review-shaped samples, must include the embedded PR diff inside `<candidate_diff>` tags plus the strict YES/NO + `<review>` schema.
- `"agent_name"`: string — kebab-case name describing the restriction (e.g. `"no-bash-editor"`, `"subagent-only-reviewer"`, `"bash-only-editor"`). For `agents_md` channel this name is informational only (used in the `<filename>` of the file); for `custom_primary_agent` channel it MUST match the `name:` in the frontmatter and the run row's `agent:` field.
- `"agent_content"`: string — the rule text. For `agents_md` channel: plain markdown (typically a `## Tool Restriction` heading + bulleted rules); no YAML frontmatter required. For `custom_primary_agent` channel: must include YAML frontmatter (`name`, `mode: primary`, `description`) followed by the body. Body explicitly enumerates allowed tools AND forbidden tools. For non-trivial restrictions, **suggests the rerouting path** the model should take.
- `"channel"`: string — exactly one of `"agents_md"` or `"custom_primary_agent"`. Indicates which delivery channel the restriction rides on (the harness uses this to install the file at the right path).
- `"pre_command"`: string — bash to materialize the project the task operates on.

## Examples (4)

### Example 1 (agents_md + no_bash + editing-shape)

```
question:

In `lib/pricing.py`, change the `calculate_discount` function so it rejects negative input amounts: when `amount < 0`, raise `ValueError("amount must be non-negative")` before performing any computation. Preserve the existing behavior for `amount >= 0`.

agent_name: no-bash-editor

agent_content:

## Tool Restriction

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

### Example 2 (agents_md + no_grep_no_glob + localization-shape)

```
question:

There's a config value called `RETRY_BACKOFF_MS` referenced across this microservice. Find every file under `services/` that defines or uses it, then write `backoff_audit.md` at the repo root with one line per file, in lex order, formatted as `path: <define|use>` (e.g. `services/api/client.py: use`). End with a single trailing newline.

agent_name: no-grep-no-glob

agent_content:

## Tool Restriction

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

### Example 3 (agents_md + subagent_required + review-shape)

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

## Tool Restriction

You are a PR reviewer in a delegation-only posture. You may use: task (to delegate inspection to a subagent).

You may NOT use read, grep, glob, edit, write, or bash directly. To inspect any file beyond what's already in the user prompt's diff, dispatch a subagent via task (e.g. `task(subagent_type="explore", prompt="...")`) and synthesise its summary.

Output the YES/NO + `<review>` schema requested by the user.

channel: agents_md

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

### Example 4 (custom_primary_agent + bash_only + editing-shape)

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

channel: custom_primary_agent

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

## Notes on the schema

- **Channel `agents_md`** is the dominant soft-restriction channel in the benchmark (78% of the soft slice — 11 of 14 soft samples) and this archetype mirrors that — 3 of 4 examples use it. Generators sampling from this archetype should default to `agents_md` unless the scenario specifically benefits from a custom primary agent (full system-prompt replacement, agent identity reframing).
- **Channel `custom_primary_agent`** replaces the default agent's system prompt entirely and requires both the `mode: primary` frontmatter and a matching `agent:` field on the run row. Use it when the restriction is strong enough to warrant a complete identity reframe ("you are a strict bash-only editor"); use `agents_md` for additive policy text on top of the default agent.
- **Parent task shape variety** matters: tool_restriction is layered on top of localization / editing / review tasks in the benchmark, so the archetype includes one example of each shape combined with a restriction. The localization example (#2) carries the structured-artifact pattern; the editing examples (#1, #4) carry behavior contracts; the review example (#3) carries the YES/NO + `<review>` schema from archetype 12 plus the subagent-required restriction.
- **Restriction shape coverage** spans no_bash (Ex 1), no_grep_no_glob (Ex 2), subagent_required (Ex 3), bash_only (Ex 4) — the 4 most common shapes in the benchmark, together accounting for ~63% of `tool_restriction` samples. Generators may extend with `no_write`, `no_glob` alone, or `parent_no_read` (rarer shapes from the same restriction family); the patterns transfer.
- **For `*_system` mutation kinds** (16 of 30 benchmark samples = 53%) the restriction is enforced by the *hard* mechanism — `opencode.json` `permission` config that removes the tool from the model's schema entirely. That is **archetype 11's** territory, not this one. The two archetypes are complementary: 11 covers schema-gating (model literally cannot see the tool); 13 covers prompted compliance (model sees the tool but is told not to use it).

## Overlap notes

All four examples use synthetic projects and synthetic identifiers:
- `calculate_discount` in synthetic `lib/pricing.py` (Ex 1)
- `RETRY_BACKOFF_MS` audit on synthetic microservice (Ex 2)
- `RateLimiter.allow` in synthetic Python `service/limit.py` (Ex 3)
- `Sum` / `format_bytes` in synthetic Go `internal/util/` (Ex 4)

None of these match v1 benchmark function names, file paths, or skill names. The benchmark's `tool_restriction` samples target callers of `merge_cookies`, `Session.prepare_request`, `RequestsCookieJar.update`, `iter_slices`, `unquote_header_value`, etc. — all explicitly avoided here.

The four examples deliberately span both soft injection channels (`agents_md`, `custom_primary_agent`) in a 3/1 ratio that approximates the benchmark's soft-channel split (11/3). They also span localization, editing, and review parent shapes (1/2/1) so the trained model learns that tool restrictions compose with each underlying task type.
