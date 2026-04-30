# Archetype 14 — `structured_artifact_output` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), some tasks require the assistant to write a **strictly-formatted artifact file** that downstream tooling (a grader, a CI step, another script) consumes verbatim. The training signal is *format precision* — getting the file path, the per-line schema, the sort order, and the trailing-newline discipline exactly right — distinct from "find the answer," which the model might already do well in a free-form chat reply.

The artifact format follows a fixed grammar typical of code-localization and audit deliverables:

- `**location.txt`-style code-locator output** — one line per matching function, format `repo/relative/path.ext::QualifiedName`, lexicographic order, trailing newline. Module-level functions are bare names; methods on a class are `ClassName.method`; closures defined inside a function are `outer.inner`.
- `**audit.tsv`-style structured findings** — tab-separated per row, fixed column order (e.g. `severity\tfile\tline\trule_id`), lex-sorted, header row optional but consistent.
- `**paths.txt`-style file enumeration** — one repo-relative path per line, lex-sorted, no leading `./`, trailing newline.
- **Constants-summary file** — Python or Go file containing only top-level `CONSTANT = value` lines with values pulled from the source under audit.

The task language describes the *content* the model must surface; the agent prompt or task framing pins the *format* explicitly. The model must search, identify the right entries, then produce the artifact in exact form. Free-form prose answers do not satisfy the task — only the file content is graded.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — describes the search/audit task and **explicitly specifies the deliverable file path and its per-line format**, including: file name, where to write it (repo root), each line's grammar with concrete examples (e.g. "module-level functions use their bare name; methods on a class use `ClassName.method`"), sort order, and trailing-newline rule.
- `"expected_output_path"`: string — the exact file path the artifact must be written to (e.g. `"location.txt"`).
- `"expected_output_content"`: string — the exact content the artifact must contain (this is the ground-truth gold string, with trailing newline if required). Used by the harness to derive the anchored regex check.
- `"pre_command"`: string — bash to materialize a non-trivial code surface (≥3 files, ≥10 lines each) so search and qualname resolution are non-trivial.

## Examples (3)

### Example 1 (function locator with class methods + closures)

```
question: In this codebase, write `location.txt` at the repo root listing — one per line, in lexicographic order — every function in src/ whose body directly calls the helper function `combine_maps` defined in src/lib/maps.py.

Each line is `file_path::QualifiedName`:
- Module-level function → bare name (e.g. `combine_maps`).
- Method on a class → `ClassName.method` (e.g. `RegistryService.bootstrap`).
- Nested closure inside another function → `outer.inner` (e.g. `RegistryService.spawn.with_defaults`).

End with a single trailing newline. Do not list any other content.

expected_output_path: location.txt

expected_output_content:

src/api/handlers.py::combine_user_settings
src/api/server.py::RegistryService.bootstrap
src/api/server.py::RegistryService.spawn.with_defaults

pre_command:

mkdir -p src/lib src/api && cat > src/lib/maps.py << 'EOF'
def combine_maps(a, b):
    out = dict(a or {})
    out.update(b or {})
    return out

def split_settings(s):
    return [p.strip() for p in s.split(",")]
EOF
cat > src/api/handlers.py << 'EOF'
from src.lib.maps import combine_maps, split_settings

def combine_user_settings(user_a, user_b):
    return combine_maps(user_a.settings, user_b.settings)

def list_users():
    return ["alice", "bob"]
EOF
cat > src/api/server.py << 'EOF'
from src.lib.maps import combine_maps

class RegistryService:
    def __init__(self):
        self.defaults = {"timeout": 30}

    def bootstrap(self, overrides):
        self.config = combine_maps(self.defaults, overrides)

    def spawn(self, request):
        def with_defaults(payload):
            return combine_maps({"version": 1}, payload)
        return with_defaults(request.body)
EOF
```

### Example 2 (paths-only enumeration)

```
question: Write `migration_targets.txt` at the repo root listing — one repo-relative path per line, lexicographic order, no leading `./` — every file under src/ that imports from `deprecated_lib`. End with a single trailing newline. List nothing else.

expected_output_path: migration_targets.txt

expected_output_content:

src/handlers/login.py
src/utils/format.py

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

### Example 3 (constants-summary file)

```
question: Inspect `config/limits.py` and write a file `summary.py` at the repo root containing exactly five module-level Python constants, in this order:

  TIMEOUT_SEC = <value>
  MAX_ATTEMPTS = <value>
  BACKOFF_BASE_MS = <value>
  WORKER_POOL_SIZE = <value>
  TARGET_REGION = <value>

Pull the values from the source. Do not include comments, imports, or any other code in summary.py. End with a single trailing newline.

expected_output_path: summary.py

expected_output_content:

TIMEOUT_SEC = 30
MAX_ATTEMPTS = 5
BACKOFF_BASE_MS = 250
WORKER_POOL_SIZE = 16
TARGET_REGION = "us-west-2"

pre_command:

mkdir -p config && cat > config/limits.py << 'EOF'
import os

# Network timeouts and retries
TIMEOUT_SEC = 30
MAX_ATTEMPTS = 5
BACKOFF_BASE_MS = 250

# Pool sizing
WORKER_POOL_SIZE = 16

# Deployment region (overridable via env)
TARGET_REGION = os.environ.get("AWS_REGION", "us-west-2")

# Internal flag (don't include in summary)
_DEBUG = False
EOF
```

## Overlap notes

All three examples use synthetic projects:

- Example 1: `combine_maps` / `combine_user_settings` / `RegistryService.bootstrap` / `RegistryService.spawn.with_defaults` — synthetic. No collision with benchmark function names like `merge_cookies`, `Session.prepare_request`, `RequestsCookieJar.update`, etc. The deliverable file `location.txt` is the same name the benchmark uses, but the *content* is unrelated.
- Example 2: `deprecated_lib` import audit — synthetic. Deliverable file `migration_targets.txt` is not used by any v1 benchmark sample.
- Example 3: synthetic `config/limits.py` with synthetic constant names (`TIMEOUT_SEC`, `MAX_ATTEMPTS`, `BACKOFF_BASE_MS`, `WORKER_POOL_SIZE`, `TARGET_REGION`). Deliverable `summary.py` does not collide with any benchmark deliverable (which include `audit.py`, `combined.py`, `consistency.md`, `report.md`, etc.).

The dotted-qualname grammar (`Class.method`, `outer.inner`) matches what v1 localization samples expect, but no benchmark scenario, function, or file path is reused.