# Archetype 13 — `tool_restriction_rerouting` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), tool restrictions are enforced through three orthogonal channels — top-level system prompt, an `AGENTS.md` file at the project root, or a custom primary-agent persona at `.opencode/agent/<name>.md`. This archetype specifically covers situations where the **natural tool for the task is denied**, forcing the assistant to **reroute through a less-obvious tool** to accomplish the same goal. The training signal is *creative compliance under restriction*, not just respect of the restriction.

Common rerouting patterns the assistant must learn:

- **`write` denied → create new file via `bash`** (`echo > file`, `cat > file <<EOF`) **or via `edit` in new-file mode** (empty `oldString`).
- **`grep` and/or `glob` denied → search via `bash`** (`rg`, `find`, `ls -R`, `grep -r`) **or via plain `read`** of suspected files.
- **`bash` denied → all operations via specialised tools** (no shell-out for verification, no `git` commands, no package-manager invocation).
- **Parent-agent file reading denied → delegate reads via `task`** to a subagent that itself uses `read`. The parent must NOT shortcut by reading directly even once.
- **`bash`-only mode → search/read/write all via `bash`** — `rg` for search, `cat` for read, `tee` / `>` for write — even though specialised tools would be more natural.
- **`read` allowed but `edit`/`write` forbidden ("read-only investigation") → produce a written analysis or finding without touching the codebase**, even when the natural reflex is to fix what's found.

The user's task should be a **normal coding/search/triage task** that would naturally invite the forbidden tool; the agent prompt enforces the restriction in one of the three channels. The deliverable should be a tangible artifact (a written file, a structured response) so the model can't satisfice with a chat-style answer that sidesteps the restriction.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — a normal coding/search/triage task. Describes the goal, NOT the constraint.
- `"agent_name"`: string — kebab-case name describing the restriction (e.g. `"no-write-edit-locator"`, `"bash-only-searcher"`, `"subagent-delegated-reader"`).
- `"agent_content"`: string — markdown with YAML frontmatter (`mode: primary`). Body explicitly enumerates allowed tools AND forbidden tools, AND **suggests the rerouting path** the assistant should take (e.g. "If you need to create a new file, use `bash echo > path` or `edit` with empty oldString").
- `"channel"`: string — exactly one of `"system_prompt"`, `"agents_md"`, `"persona"`. Indicates which delivery channel the restriction rides on (the harness uses this to install the restriction in the right place).
- `"pre_command"`: string — bash to materialize the project the task operates on.

## Examples (4)

### Example 1 (write denied → bash echo or edit-as-create)

```
question: Find every file under src/ that imports from "deprecated_lib" and write a list of those file paths, one per line, to a new file at the repo root called migration_targets.txt.

agent_name: no-write-bash-locator

agent_content:

---
name: no-write-bash-locator
mode: primary
description: Locator agent that may not use the write tool. New files are created via bash or edit.
---
You may use these tools: read, grep, glob, bash, edit, task.

You may NOT use the write tool. If you need to create a new file, do one of:
- `bash` with `echo "..." > path` or `cat > path <<EOF ... EOF`.
- `edit` with an empty `oldString` and the desired content as `newString` (this creates the file).

This restriction applies for the entire session.

channel: persona

pre_command:

mkdir -p src/handlers src/utils && cat > src/handlers/login.py << 'EOF'
from deprecated_lib import old_auth
def login(u): return old_auth(u)
EOF
cat > src/handlers/billing.py << 'EOF'
from new_lib import charge
def bill(u, amt): return charge(u, amt)
EOF
cat > src/utils/format.py << 'EOF'
from deprecated_lib import legacy_fmt
def fmt(x): return legacy_fmt(x)
EOF
cat > src/utils/log.py << 'EOF'
import logging
def log(m): logging.info(m)
EOF
```

### Example 2 (grep + glob denied via AGENTS.md → bash search or pure read)

```
question: There's a config value called RETRY_BACKOFF_MS sprinkled across this microservice. Find every file that defines or uses it, and write a one-line summary per file to backoff_audit.md at the repo root.

agent_name: bash-search-only

agent_content:

---
name: bash-search-only
mode: primary
description: Search agent that uses bash for searching instead of grep/glob.
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

### Example 3 (parent-read denied → delegate to subagent via task)

```
question: Explain what the BackgroundQueue.flush_all method does in pkg/queue/queue.go — give me a 5-line summary plus a list of the helper functions it calls.

agent_name: delegated-reader

agent_content:

---
name: delegated-reader
mode: primary
description: Coordinator that never reads files directly; all reads go through a subagent.
---
You may use: bash (for `git`, build, lint only), edit, write, task.

You may NOT use read, grep, or glob directly. Whenever you need to inspect a file, dispatch a subagent via the task tool (e.g. `task(subagent_type="explore", prompt="read pkg/queue/queue.go and report ...")`) and rely on the subagent's returned summary.

This applies to ALL file inspection — including the very first lookup. Never shortcut by reading once "to get oriented".

channel: system_prompt

pre_command:

mkdir -p pkg/queue && cat > pkg/queue/queue.go << 'EOF'
package queue

import (
	"sync"
	"time"
)

type BackgroundQueue struct {
	mu    sync.Mutex
	jobs  []func()
	clock func() time.Time
}

func (q *BackgroundQueue) take() func() {
	q.mu.Lock()
	defer q.mu.Unlock()
	if len(q.jobs) == 0 { return nil }
	j := q.jobs[0]
	q.jobs = q.jobs[1:]
	return j
}

func (q *BackgroundQueue) record(start time.Time) {
	_ = q.clock()
	_ = start
}

// FlushAll drains the queue, running every pending job to completion.
func (q *BackgroundQueue) FlushAll() {
	for {
		j := q.take()
		if j == nil { return }
		start := time.Now()
		j()
		q.record(start)
	}
}
EOF
cat > go.mod << 'EOF'
module example.com/q
go 1.21
EOF
```

### Example 4 (bash-only via persona → everything via shell)

```
question: Add a function format_bytes(n: int64) string to internal/util/util.go that turns a byte count into a human-readable string ("1.5 MB", "723 B"), and a corresponding test in internal/util/util_test.go.

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

## Overlap notes

All four examples use synthetic projects:
- `deprecated_lib` / `new_lib` import audit on synthetic Python services.
- `RETRY_BACKOFF_MS` audit on synthetic microservice.
- `BackgroundQueue.flush_all` in synthetic Go queue package.
- `Sum` / `format_bytes` in synthetic Go internal package.

None of these match v1 benchmark function names. The benchmark's `tool_restriction` hard-tier samples target callers of `merge_cookies`, `Session.prepare_request`, `RequestsCookieJar.update`, and similar — all explicitly avoided here.

The four examples deliberately span all three injection channels (`system_prompt`, `agents_md`, `persona` — Example 4 uses persona, Example 3 uses system_prompt, Example 2 uses agents_md, Example 1 uses persona) so the trained model learns the same constraint transfers across delivery mechanisms — mirroring v1's `_system` / `agents_md_*` / `persona_main_*` mutation kinds.
