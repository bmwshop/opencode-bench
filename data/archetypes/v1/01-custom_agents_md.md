# Archetype 01 — `custom_agents_md`

## Description

In OpenCode (an agentic CLI similar to Claude Code), an `AGENTS.md` file at the project root has its content automatically appended to the assistant's system prompt at startup, so every response in that project must obey those rules. This archetype covers a normal coding task in a project that has such an `AGENTS.md`.

`AGENTS.md` rules can cover any project-level concern. Common rule families (illustrative, not exhaustive — real `AGENTS.md` files often go beyond them):

- **Style & naming** — formatting/indentation, naming conventions, banned syntax, formatter/linter rules
- **Testing** — test-framework choice, coverage targets, test layout and naming, fixture/mocking rules, what to test for what
- **Documentation** — docstring/comment style, where READMEs/CHANGELOGs/ADRs live, required API-doc sections
- **File organisation** — directory layout, where new modules/components/migrations go, layer boundaries, file naming and size limits
- **Error handling** — error types/classes to use, logger choice, propagation patterns, banned patterns (raw `print`, `panic`, swallowed errors)
- **Dependencies** — preferred/banned packages, license rules, version-pinning policy, lockfile and vendor rules
- **Output formatting** — response/payload shape, key casing, error and log-line formats, status-code conventions
- **Security** — secret handling, input validation/sanitization, authn/authz patterns, banned dangerous APIs (`eval`, raw SQL string-interp), audit logging
- **Performance** — banned slow patterns (sync I/O, N+1 queries), caching/batching policies, async/streaming requirements, query and memory limits
- **Project-specific commands** — how to run tests/lint/build (`cargo test`, `make check`), required pre-commit checks, release commands
- **Tool preferences / restrictions** — which built-in tools the assistant should prefer, avoid, or never use ("use `bash` only for builds and tests; otherwise prefer read/edit/write/grep/glob", "never use the `task` tool"). All tools remain visible in the schema; the rule is enforced by the `AGENTS.md` content alone.

Pick one or two related families per sample; the coding task itself is completable on its own.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the user's request.
- `"agent_prompt"`: string — content for `AGENTS.md`. 3–15 lines using markdown headers and bullets.
- `"pre_command"`: string — bash to create any files the question references; empty string if from-scratch.

## Examples (6)

### Example 1

```
question: Add a --json flag to scripts/report.py that makes the output machine-readable JSON (one object per row) instead of the current tab-separated text, and document the flag in the README.

agent_prompt:

## Style & Conventions

- Use 4-space indentation. No tabs.
- All public functions must have Google-style docstrings with Args / Returns / Raises sections.
- Errors must go through `logging.getLogger(__name__).error(...)`; never use `print` for errors.
- Any new CLI flag must be documented in README.md under the ## Usage section, with a one-line description and an example invocation.
- Prefer the standard library; do not add third-party dependencies without a comment justifying why.

pre_command:

mkdir -p scripts && cat > scripts/report.py << 'EOF'
import csv, sys

def main(path):
    with open(path) as f:
        for row in csv.DictReader(f):
            print(f"{row['id']}\t{row['name']}\t{row['count']}")

if __name__ == '__main__':
    main(sys.argv[1])
EOF
cat > README.md << 'EOF'
# Project reporter

## Usage

Run `python scripts/report.py data.csv` to print a tab-separated report.
EOF
```

### Example 2

```
question: Add a function FormatBytes(n int64) string to internal/util that turns a byte count into a human-readable string like "1.5 MB" or "723 B".

agent_prompt:

## Testing Rules

- Every public function under internal/ must have a corresponding *_test.go file in the same package.
- Use table-driven tests; minimum 4 cases including: zero, negative, the largest representative input, and at least one boundary case between units.
- Run `go test -race ./...` before considering the change done.
- Don't add new exported names without a godoc comment ending in a period.
- Test files must not import any package that is not already in go.sum.

pre_command:

mkdir -p internal/util && cat > internal/util/util.go << 'EOF'
package util

// Sum returns the sum of a slice of ints.
func Sum(xs []int) int {
    total := 0
    for _, x := range xs {
        total += x
    }
    return total
}
EOF
cat > internal/util/util_test.go << 'EOF'
package util

import "testing"

func TestSum(t *testing.T) {
    cases := []struct {
        in   []int
        want int
    }{
        {nil, 0},
        {[]int{}, 0},
        {[]int{1, 2, 3}, 6},
        {[]int{-1, 1}, 0},
    }
    for _, c := range cases {
        if got := Sum(c.in); got != c.want {
            t.Errorf("Sum(%v) = %d, want %d", c.in, got, c.want)
        }
    }
}
EOF
cat > go.mod << 'EOF'
module example.com/proj

go 1.22
EOF
```

### Example 3

```
question: Add a /healthz endpoint to src/server.ts that returns the service version, uptime in seconds, and a flag for whether the database is reachable.

agent_prompt:

## API & Logging Conventions

- All HTTP responses are JSON with `snake_case` keys.
- All HTTP endpoints documented in `docs/api.md` under the `## Endpoints` heading; include path, method, request, response.
- Never `console.log` from production code paths — use the project logger from `src/log.ts`.
- Update `CHANGELOG.md` under the `## [Unreleased]` section with a one-line entry for any user-visible change.
- New runtime dependencies require a comment in package.json explaining why; never add a dep that duplicates an existing one.

pre_command:

mkdir -p src docs && cat > src/server.ts << 'EOF'
import express from 'express';
import { log } from './log';

export const VERSION = '1.4.2';
const app = express();

app.get('/api/items', (req, res) => {
  log.info('list_items');
  res.json({ items: [] });
});

app.listen(8080);
EOF
cat > src/log.ts << 'EOF'
export const log = {
  info: (msg: string, meta?: object) => process.stdout.write(JSON.stringify({ level: 'info', msg, ...meta }) + '\n'),
  error: (msg: string, meta?: object) => process.stderr.write(JSON.stringify({ level: 'error', msg, ...meta }) + '\n'),
};
EOF
cat > docs/api.md << 'EOF'
# API

## Endpoints

### GET /api/items
Returns the list of items.
Response: { "items": [] }
EOF
cat > CHANGELOG.md << 'EOF'
# Changelog

## [Unreleased]
EOF
```

### Example 4

```
question: Add a function parse_users(path: &Path) -> Result<Vec<User>, AppError> that reads a CSV file and returns the parsed users. Handle missing files, malformed rows, and bad email formats with appropriate AppError variants.

agent_prompt:

## Project layout

- Domain types live under `src/domain/`; one file per type, re-exported from `src/domain/mod.rs`.
- I/O code lives under `src/io/`; never call `std::fs` from `src/domain/`.
- The public API of the crate is re-exported from `src/lib.rs` only.

## Error handling

- Every function that can fail must return `Result<T, AppError>`. `AppError` is the project-wide enum in `src/error.rs`; add new variants there as needed.
- Never use `unwrap()` or `expect()` outside `#[cfg(test)]`.
- Propagate errors with `?`; never silently discard an error.

## Commands

- Tests: `cargo test --all`
- Lint: `cargo clippy --all-targets -- -D warnings`
- Run both before considering a change complete.

pre_command:

mkdir -p src/domain src/io && cat > Cargo.toml <<'EOF'
[package]
name = "users"
version = "0.1.0"
edition = "2021"
EOF
cat > src/lib.rs <<'EOF'
pub mod domain;
pub mod io;
pub mod error;

pub use domain::User;
pub use error::AppError;
EOF
cat > src/error.rs <<'EOF'
use std::io;

#[derive(Debug)]
pub enum AppError {
    Io(io::Error),
    Parse(String),
}

impl From<io::Error> for AppError {
    fn from(e: io::Error) -> Self { AppError::Io(e) }
}
EOF
cat > src/domain/mod.rs <<'EOF'
pub mod user;
pub use user::User;
EOF
cat > src/domain/user.rs <<'EOF'
pub struct User {
    pub email: String,
    pub name: String,
}
EOF
cat > src/io/mod.rs <<'EOF'
EOF
```

### Example 5

```
question: Add a /users/search endpoint that returns users whose username starts with a given prefix. Cap results at 50 per request.

agent_prompt:

## Security

- All database queries must use the ORM or parameterised SQL; never interpolate user input into a raw SQL string.
- All user-supplied identifiers (usernames, emails, IDs) are validated before use: enforce length and character allowlists.
- Secrets are read from `os.environ`; never hardcode and never log them. Use the existing `settings.get_secret(name)` helper.
- Banned APIs in production code: `eval`, `exec`, `subprocess` with `shell=True`, `pickle.loads` on untrusted input.

## Performance

- N+1 query patterns are forbidden — use `select_related` or `prefetch_related` for related-object access.
- Endpoints that return lists must enforce a `LIMIT` on the database query, not by trimming the result list in Python.
- Avoid loading entire tables into memory; paginate or stream.

pre_command:

mkdir -p api && cat > api/models.py <<'EOF'
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=64, unique=True)
    email = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    body = models.TextField()
EOF
cat > api/views.py <<'EOF'
from django.http import JsonResponse
from .models import User

def get_user(request, user_id):
    u = User.objects.get(id=user_id)
    return JsonResponse({'id': u.id, 'username': u.username, 'email': u.email})
EOF
cat > api/urls.py <<'EOF'
from django.urls import path
from . import views

urlpatterns = [
    path('users/<int:user_id>/', views.get_user),
]
EOF
```

### Example 6

```
question: Add a --watch flag to scripts/build.sh so it rebuilds whenever a file under src/ changes. Document the flag in README.md.

agent_prompt:

## Tool conventions

- For any file inspection or modification, use the dedicated tools — `read`, `write`, `edit`, `grep`, `glob`. Do NOT use `bash` for file I/O (no `cat`, `sed`, `awk`, `>`-redirects).
- `bash` is reserved for: running build/test/lint commands, `git` operations, package managers (`npm`, `pip`).
- Never use the `task` tool — keep all work in this conversation.

## Documentation

- Every flag added to a script must be documented in `README.md` under `## Usage`, with a one-line description and an example invocation.

pre_command:

mkdir -p scripts src && cat > scripts/build.sh <<'EOF'
#!/usr/bin/env bash
set -e
src_dir=${1:-src}
out_dir=${2:-dist}
mkdir -p "$out_dir"
npx tsc --outDir "$out_dir" "$src_dir"/*.ts
EOF
chmod +x scripts/build.sh
cat > src/index.ts <<'EOF'
export const VERSION = '0.1.0';
export function greet(name: string): string { return `hello, ${name}`; }
EOF
cat > package.json <<'EOF'
{
  "name": "watcher",
  "version": "0.1.0",
  "devDependencies": { "typescript": "^5.4.0" }
}
EOF
cat > README.md <<'EOF'
# Watcher

## Usage

Run `scripts/build.sh src dist` to compile sources to dist.
EOF
```

## Overlap notes

All six examples are synthetic projects with no overlap against benchmark identifiers. Tasks: `--json` flag on a generic `report.py`, Go `Sum`/`FormatBytes` helper, Express `/healthz`, Rust `parse_users`, Django `/users/search`, shell `--watch` flag. None of these match v1 benchmark function names, file paths, or scenarios.
