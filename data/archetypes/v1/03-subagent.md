# Archetype 03 — `subagent`

## Description

In OpenCode (an agentic CLI similar to Claude Code), a custom subagent is a markdown file (typically under `.opencode/agent/<name>.md`) with `mode: subagent` frontmatter. The assistant delegates to it via the `task` tool: calling `task(subagent_type='<name>', prompt='...')` spawns a fresh conversation with the subagent's system prompt and returns its final reply.

Subagents are specialists. Common subagent families:

- **Code reviewer** — reviews a file/diff for bugs, style, security
- **Test writer** — given a function/module, writes tests in the project's framework
- **Doc generator** — produces user-facing markdown from public APIs
- **Security auditor** — focused vulnerability scan on a file/area
- **Concurrency / race-condition specialist** (Go, Rust, Java, Python asyncio)
- **Performance / profiling specialist** — looks for slow patterns
- **Type checker** — checks consistency with existing types, tightens signatures
- **Accessibility reviewer** — checks UI components for a11y rules
- **Migration / upgrade helper** — converts old API usage to new API
- **Refactoring specialist** — extracts modules, splits files, renames symbols

Pick a specialty that fits the user's task so delegation is the natural choice.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the user's request, naturally calling for the named subagent's specialty.
- `"subagent_name"`: string — kebab-case subagent name (e.g. `"reviewer"`, `"concurrency-reviewer"`, `"test-writer"`).
- `"subagent_content"`: string — full markdown with YAML frontmatter (`name`, `mode: "subagent"`, `description`) and a body defining the subagent's approach.
- `"pre_command"`: string — bash to create source files the task operates on.

## Examples (3)

### Example 1

```
question: I just refactored internal/queue/worker.go to use a bounded channel for backpressure. Can you have it reviewed for concurrency issues?

subagent_name: concurrency-reviewer

subagent_content:

---
name: concurrency-reviewer
mode: subagent
description: Go concurrency specialist — finds data races, goroutine leaks, channel misuse, deadlocks, and unsafe map access.
---
You review Go code for concurrency issues. For each file you look at, report:
- Data races (name the involved goroutines and shared state).
- Goroutine leaks (places where a goroutine has no exit path).
- Unbuffered vs. bounded channel misuse.
- Deadlocks or lock-ordering bugs.
- Unsafe concurrent access to maps/slices.

Give concrete `file:line` references. If unsure, run `go vet` and include its output.

pre_command:

mkdir -p internal/queue && cat > internal/queue/worker.go << 'EOF'
package queue

import (
    "context"
    "sync"
    "time"
)

type Job struct{ ID string; Payload []byte }

type Pool struct {
    jobs    chan Job
    results map[string]error
    wg      sync.WaitGroup
}

func NewPool(size, buf int) *Pool {
    return &Pool{jobs: make(chan Job, buf), results: map[string]error{}}
}

func (p *Pool) Start(ctx context.Context, n int) {
    for i := 0; i < n; i++ {
        p.wg.Add(1)
        go func() {
            defer p.wg.Done()
            for j := range p.jobs {
                err := process(j)
                p.results[j.ID] = err
            }
        }()
    }
}

func (p *Pool) Submit(j Job) { p.jobs <- j }

func process(j Job) error { time.Sleep(10 * time.Millisecond); return nil }
EOF
```

### Example 2

```
question: I added a parse_duration() helper in src/utils.py that turns strings like "1h30m" or "45s" into seconds. Can you write tests for it?

subagent_name: test-writer

subagent_content:

---
name: test-writer
mode: subagent
description: Test author — writes thorough pytest tests with parametrized cases, edge cases, and error paths.
---
You write tests using pytest. For each function under review:
- Use `@pytest.mark.parametrize` for happy-path cases (at least 5).
- Add a separate test (or parametrized cases) for each error path the function may raise.
- Cover edge cases: empty input, zero, negative, max, off-by-one, unicode, whitespace.
- Use `pytest.approx(...)` for floats.
- Place tests in `tests/test_<module>.py`. Match the project's existing import style.
- After writing tests, run `pytest -q` and include any failures verbatim.

pre_command:

mkdir -p src tests && cat > src/utils.py << 'EOF'
import re

_PATTERN = re.compile(r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$')

def parse_duration(s: str) -> int:
    """Parse strings like '1h30m', '45s', '2h', '15m' into seconds."""
    if not s:
        raise ValueError('empty duration')
    m = _PATTERN.fullmatch(s.strip())
    if not m or s.strip() == '':
        raise ValueError(f'invalid duration: {s!r}')
    h, mm, ss = (int(x) if x else 0 for x in m.groups())
    if h == 0 and mm == 0 and ss == 0:
        raise ValueError(f'duration is zero or unparsable: {s!r}')
    return h * 3600 + mm * 60 + ss
EOF
cat > pyproject.toml << 'EOF'
[project]
name = "proj"
version = "0.1.0"
[tool.pytest.ini_options]
testpaths = ["tests"]
EOF
```

### Example 3

```
question: Generate user-facing README documentation for the public functions exported from pkg/auth/. The README should help a new user log in, refresh a token, and check whether they're authenticated.

subagent_name: doc-generator

subagent_content:

---
name: doc-generator
mode: subagent
description: User-facing documentation generator — turns public API surfaces into clear README sections with runnable examples.
---
You write user-facing documentation from a code surface. Workflow:
1. Read the package's exported functions/types.
2. For each public function, write: a one-line summary, signature in a fenced code block, parameters, return value, and a short example call.
3. Group functions by user goal (e.g. 'Authenticating', 'Managing sessions') rather than by file.
4. Open with a 'Quick start' section showing the most common end-to-end usage.
5. Skip internal/private symbols entirely.
6. Output as a single Markdown document.

pre_command:

mkdir -p pkg/auth && cat > pkg/auth/auth.go << 'EOF'
// Package auth provides session-token authentication.
package auth

import (
    "errors"
    "time"
)

// Token is an opaque session token issued by Login.
type Token struct {
    Value     string
    ExpiresAt time.Time
}

// Login authenticates a user and returns a fresh Token.
func Login(username, password string) (*Token, error) {
    if username == "" || password == "" {
        return nil, errors.New("username and password required")
    }
    return &Token{Value: "tok_" + username, ExpiresAt: time.Now().Add(1 * time.Hour)}, nil
}

// Refresh extends the lifetime of a Token.
func Refresh(t *Token) (*Token, error) {
    if t == nil { return nil, errors.New("nil token") }
    return &Token{Value: t.Value, ExpiresAt: time.Now().Add(1 * time.Hour)}, nil
}

// IsValid reports whether the token has not yet expired.
func IsValid(t *Token) bool {
    return t != nil && time.Now().Before(t.ExpiresAt)
}

// internalReap is unexported and not part of the public API.
func internalReap() {}
EOF
cat > go.mod << 'EOF'
module example.com/auth

go 1.22
EOF
```

## Overlap notes

All three subagents (`concurrency-reviewer`, `test-writer`, `doc-generator`) operate on synthetic projects: a Go bounded-channel worker pool, a Python `parse_duration` helper, and a Go session-token API in `pkg/auth/auth.go`. None of these target v1 benchmark function names, files, or scenarios.
