# Archetype 14 — `code_localization_artifact` (NEW)

## Description

This archetype trains the **strict `location.txt` artifact format used by every v1 `code_localization` benchmark sample** (#21–#50, plus mutants). Across all 30 benchmark samples, the deliverable is identical in shape:

- **Filename:** `location.txt` at the repo root
- **Per-line grammar:** `repo/relative/path.ext::QualifiedName`
- **Qualified-name discipline:**
    - Module-level function → bare name (e.g. `normalize_amount`)
    - Method on a class → `ClassName.method` (e.g. `Server.handle_request`)
    - Method on a mixin → `MixinName.method` (e.g. `LoggableMixin.write_log`)
    - Closure defined inside another function → `outer.inner` (e.g. `process_batch.with_retry`)
- **Sort:** lexicographic across the entire output
- **Trailing newline:** required (anchored regex `\A...\n?\Z`)
- **No extra content:** the grader uses an anchored regex that rejects any deviation

The training signal is *format precision* — getting the file path, the per-line schema, the sort order, and the trailing-newline discipline exactly right — distinct from "find the answer," which the model often does well in a free-form chat reply but fails to render in the strict format.

### Two templates the benchmark uses

The benchmark splits its 30 samples between two templates:

- **T1 — anchor + direct callers** (23 of 30 samples = 77%): one anchor function is named (or described). The answer is the anchor *itself* (as `file::QualifiedName`) plus every function under the declared scope whose body contains a direct call resolving by name to the anchor.
- **T2 — callers-of-set** (7 of 30 = 23%): a *set* of target names is given (e.g., the exports of a particular module). The answer is every function under scope whose body calls *any* target. The target defs themselves are NOT in the answer (this is the distinction from T1).

Both templates use the identical artifact format above. The archetype includes one example of each prevalent template + scope + anchor combination.

## Distribution targets (mirror v1 `code_localization` benchmark)

| axis | benchmark | this archetype (3 examples) |
|---|---|---|
| **template** — T1 / T2 | 23 / 7 (77 / 23%) | 2 / 1 (67 / 33%) |
| **scope_kind** — single_file / two_files / three_files / any_file / etc. | 11 / 6 / 3 / 8 / 2 (37 / 20 / 10 / 27 / 6%) | 1 / 1 / 0 / 1 / 0 |
| **anchor_kind** — module_level / instance_method / mixin_method / none (T2) | 12 / 9 / 2 / 7 (40 / 30 / 7 / 23%) | 1 / 1 / 0 / 1 |
| **difficulty** — easy / medium / hard | 11 / 10 / 9 | 1 / 1 / 1 |
| **answer_entries** | 2–8 (mode = 3) | 4 / 3 / 3 |

The 3 examples below cover the dominant T1/T2 split, the two most common anchor kinds (module_level + instance_method), three different scope shapes, and one of each difficulty tier. Generators can extend with more examples to cover rarer shapes (mixin_method anchor, three_files scope, etc.) — the artifact grammar is identical across all of them.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — describes the search task and **explicitly specifies the deliverable file path and its per-line format**, including: file name (`location.txt`), where to write it (repo root), the `file::QualifiedName` grammar with concrete examples for each qualname kind (bare / ClassName.method / outer.inner), sort order (lex), and trailing-newline rule.
- `"expected_output_path"`: string — exactly `"location.txt"`.
- `"expected_output_content"`: string — the exact content the artifact must contain (the gold string, with trailing newline). Used by the harness to derive the anchored `\A...\n?\Z` regex check.
- `"structural_signature"`: object — declares the structural axes the sample exercises:
    - `"template"`: `"T1"` or `"T2"`
    - `"scope_kind"`: e.g. `"single_file"`, `"two_files"`, `"any_file"` (matches benchmark vocabulary)
    - `"anchor_kind"`: `"module_level"`, `"instance_method"`, `"mixin_method"`, or `null` for T2
    - `"answer_entries"`: integer count of lines in the gold
    - `"difficulty"`: `"easy"` / `"medium"` / `"hard"`
- `"pre_command"`: string — bash to materialize a non-trivial code surface (≥3 files for multi-file scope; sufficient surrounding callers / non-callers so the search isn't trivially `grep -l`).

## Examples (3)

### Example 1 (T1 + single_file + module_level + easy)

```
question:

In `src/ledger/posting.py`, write `location.txt` at the repo root listing — one per line, in lexicographic order — every function in that file (any nesting depth, including methods on classes) whose body directly calls the module-level helper `normalize_amount`.

Each line is `file_path::QualifiedName`:
- Module-level functions → bare name (e.g. `normalize_amount`)
- Methods on a class → `ClassName.method`
- Nested closures inside another function → `outer.inner`

End with a single trailing newline. Do not list any other content.

expected_output_path: location.txt

expected_output_content:

src/ledger/posting.py::normalize_amount
src/ledger/posting.py::post_credit
src/ledger/posting.py::post_debit
src/ledger/posting.py::post_transfer

structural_signature:

{
  "template": "T1",
  "scope_kind": "single_file",
  "anchor_kind": "module_level",
  "answer_entries": 4,
  "difficulty": "easy"
}

pre_command:

mkdir -p src/ledger && cat > src/ledger/posting.py << 'EOF'
def normalize_amount(amount):
    """Round amount to two decimals; reject negative input."""
    if amount < 0:
        raise ValueError("amount must be non-negative")
    return round(amount, 2)

def post_credit(account, amount):
    return (account, normalize_amount(amount))

def post_debit(account, amount):
    return (account, -normalize_amount(amount))

def post_transfer(from_acc, to_acc, amount):
    a = normalize_amount(amount)
    return [(from_acc, -a), (to_acc, a)]

def list_accounts():
    return ["a", "b"]

def close_account(account):
    return None
EOF
```

### Example 2 (T1 + two_files + instance_method + medium)

```
question:

In this checkout, a `DiskCache` instance method evicts a key from the on-disk cache. Write `location.txt` at the repo root listing — one per line, in lexicographic order — every function defined in `src/io/cache.py` or `src/io/manager.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that method.

Each line is `file_path::QualifiedName`:
- Module-level functions → bare name
- Methods on a class → `ClassName.method`
- Nested closures inside another function → `outer.inner`

End with a single trailing newline.

expected_output_path: location.txt

expected_output_content:

src/io/cache.py::DiskCache.evict
src/io/cache.py::DiskCache.store
src/io/manager.py::CacheManager.refresh
src/io/manager.py::CacheManager.reset

structural_signature:

{
  "template": "T1",
  "scope_kind": "two_files",
  "anchor_kind": "instance_method",
  "answer_entries": 4,
  "difficulty": "medium"
}

pre_command:

mkdir -p src/io && cat > src/io/cache.py << 'EOF'
import os

class DiskCache:
    def __init__(self, path):
        self.path = path

    def has(self, key):
        return os.path.exists(os.path.join(self.path, key))

    def get(self, key):
        if not self.has(key):
            return None
        return open(os.path.join(self.path, key)).read()

    def evict(self, key):
        try:
            os.remove(os.path.join(self.path, key))
        except FileNotFoundError:
            pass

    def store(self, key, val):
        self.evict(key)
        with open(os.path.join(self.path, key), "w") as f:
            f.write(val)
EOF
cat > src/io/manager.py << 'EOF'
from src.io.cache import DiskCache

class CacheManager:
    def __init__(self):
        self.c = DiskCache("/tmp/cache")

    def get(self, key):
        return self.c.get(key)

    def refresh(self, key):
        self.c.evict(key)
        self.c.store(key, "v")

    def reset(self):
        for k in self._known_keys():
            self.c.evict(k)

    def _known_keys(self):
        return ["a", "b", "c"]
EOF
```

### Example 3 (T2 + any_file + callers-of-set + hard)

```
question:

In this checkout, the module `src/auth/tokens.py` exports three token-lifecycle helpers: `issue_token`, `revoke_token`, and `refresh_token`. Write `location.txt` at the repo root listing — one per line, in lexicographic order — every function defined under `src/` (any nesting depth, including methods on classes) whose body directly calls AT LEAST ONE of those three helpers.

Each line is `file_path::QualifiedName`:
- Module-level functions → bare name
- Methods on a class → `ClassName.method`
- Nested closures inside another function → `outer.inner`

The three helper definitions themselves are NOT in the answer set — only their callers. End with a single trailing newline.

expected_output_path: location.txt

expected_output_content:

src/api/login.py::handle_login
src/api/logout.py::handle_logout
src/api/refresh.py::SessionRefresher.refresh

structural_signature:

{
  "template": "T2",
  "scope_kind": "any_file",
  "anchor_kind": null,
  "answer_entries": 3,
  "difficulty": "hard"
}

pre_command:

mkdir -p src/auth src/api && cat > src/auth/tokens.py << 'EOF'
import secrets

def issue_token(user):
    return f"tok_{user}_{secrets.token_hex(4)}"

def revoke_token(tok):
    return True

def refresh_token(tok):
    return f"new_{tok}"
EOF
cat > src/api/login.py << 'EOF'
from src.auth.tokens import issue_token

def handle_login(user, password):
    if not _verify(user, password):
        return None
    return {"token": issue_token(user)}

def _verify(user, password):
    return password == "ok"
EOF
cat > src/api/logout.py << 'EOF'
from src.auth.tokens import revoke_token

def handle_logout(tok):
    revoke_token(tok)
    return {"ok": True}
EOF
cat > src/api/refresh.py << 'EOF'
from src.auth.tokens import refresh_token

class SessionRefresher:
    def __init__(self):
        self.last = None

    def refresh(self, tok):
        new = refresh_token(tok)
        self.last = new
        return new
EOF
cat > src/api/heartbeat.py << 'EOF'
def ping():
    return "pong"

def health():
    return {"status": "ok"}
EOF
```

## Notes on the schema

- **Single artifact format throughout.** Every benchmark `code_localization` sample uses `location.txt` at the repo root with `file::QualifiedName` lines, lex-sorted, trailing newline. This archetype enforces that uniformity — generators sampling from it should never produce a different filename or grammar.
- **Why both T1 and T2?** The benchmark splits 77/23 between these templates, and they require different cognitive moves: T1 is "find the anchor + every direct caller of it"; T2 is "find every function that calls *any* of these N targets." The training set should expose both shapes.
- **Why difficulty stratification?** The benchmark is balanced 11/10/9 across easy/medium/hard, and each tier exercises different challenges (single-file lookup vs. cross-file caller-fanin vs. callers-of-set across many files). Each example here carries an explicit `difficulty` so the generator can produce stratified samples.
- **Other artifact shapes (audit.tsv, paths.txt, summary.py)** that the previous version of this archetype enumerated do not appear in the v1 `code_localization` benchmark. They map closer to orchestration's audit-file pattern (`audit.py`, `report.md`, `consistency.md` in samples like `delegate_schedule_audit`). If those are needed as a training shape, they belong in a separate archetype, not here.

## Overlap notes

All three examples use synthetic projects with synthetic identifiers:

- Example 1: `normalize_amount`, `post_credit`, `post_debit`, `post_transfer` in synthetic `src/ledger/posting.py` — none of these names appear in the v1 benchmark.
- Example 2: `DiskCache.evict`, `CacheManager.refresh` in synthetic `src/io/cache.py` and `src/io/manager.py` — synthetic; no collision with benchmark identifiers like `RequestsCookieJar.update`, `Session.prepare_request`, `merge_cookies`, `SessionRedirectMixin.resolve_redirects`, etc.
- Example 3: `issue_token`, `revoke_token`, `refresh_token`, `handle_login`, `SessionRefresher.refresh` in synthetic `src/auth/`, `src/api/` — synthetic; no collision with `to_native_string`, `dispatch_hook`, `address_in_network`, `urldefragauth`, etc.

The dotted-qualname grammar (`Class.method`, `outer.inner`) intentionally matches the benchmark — that's the whole point of the archetype. But every concrete name (functions, files, classes) is distinct from the benchmark's pinned `requests` / `httpx` / `click` / `autoresearch` repos to avoid eval contamination.
