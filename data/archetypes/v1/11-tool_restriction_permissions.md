# Archetype 11 — `tool_restriction_permissions`

## Description

In OpenCode (an agentic CLI similar to Claude Code), the project's `opencode.json` can include a `permission` config that maps tool names to `'allow'` or `{'*': 'deny'}`. The permissions are read at startup, so denied tools never appear in the assistant's tool schema at all — the assistant literally cannot see them.

Common permission profiles:

- **bash-only** — `bash` allowed; `read`/`edit`/`write`/`glob`/`grep`/`task`/`todowrite` all denied
- **read-only** — `read`/`glob`/`grep` allowed; `edit`/`write`/`bash`/`task`/`todowrite` denied
- **investigate** — `read`/`grep`/`glob`/`bash` allowed; `edit`/`write`/`task`/`todowrite` denied
- **solo (no delegation)** — everything allowed except `task` and `todowrite` (no subagents, no todo lists)
- **no-bash** — `read`/`write`/`edit`/`glob`/`grep`/`task` allowed; `bash` denied (sandboxed env)
- **search-only** — `grep`/`glob` allowed; everything else denied

Because denied tools are hidden, the agent body should NOT enumerate forbidden tools — a generic 'Accomplish tasks using the tools available to you.' is fine.

How the runtime applies permissions: OpenCode reads permissions from `.opencode/opencode.json`'s `permission` block at startup. The harness writes this file from your sample's `opencode_permissions` field automatically — `pre_command` must NOT touch `.opencode/` or try to apply the permissions itself.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — a normal coding or search task.
- `"agent_name"`: string — kebab-case agent name (e.g. `"bash-strict"`, `"read-only"`, `"investigator"`).
- `"agent_content"`: string — agent markdown with YAML frontmatter (`mode: "primary"`). Body should not list forbidden tools (they don't appear); a simple "Accomplish tasks using the tools available to you." is fine.
- `"opencode_permissions"`: object — permission config for `opencode.json`. Maps tool names to `"allow"` or `{"*": "deny"}`.
- `"pre_command"`: string — bash to create files for the task.

## Examples (3)

### Example 1

```
question: List every function exported from any .ts file under src/ and show which file each export lives in.

agent_name: bash-strict

agent_content:

---
name: bash-strict
mode: primary
description: Agent with restricted tool access.
---
Accomplish tasks using the tools available to you.

opencode_permissions:

{
  "bash": "allow",
  "read": { "*": "deny" },
  "edit": { "*": "deny" },
  "glob": { "*": "deny" },
  "grep": { "*": "deny" },
  "task": { "*": "deny" },
  "todowrite": "deny"
}

pre_command:

mkdir -p src && cat > src/auth.ts << 'EOF'
export function login(u: string, p: string) { return 'token'; }
export function logout(sid: string) { return true; }
export const ADMIN_ROLE = 'admin';
EOF
cat > src/db.ts << 'EOF'
export async function connect(url: string) { return { url }; }
export function disconnect(conn: any) {}
EOF
cat > src/utils.ts << 'EOF'
export const VERSION = '2.1.0';
export function chunk<T>(a: T[], n: number): T[][] { return []; }
export function sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }
EOF
```

### Example 2

```
question: Walk through src/ and tell me which files import from a package called "oldlib". I just want the list and the line where the import sits.

agent_name: investigator

agent_content:

---
name: investigator
mode: primary
description: Investigation agent.
---
Accomplish tasks using the tools available to you.

opencode_permissions:

{
  "read": "allow",
  "grep": "allow",
  "glob": "allow",
  "bash": { "*": "deny" },
  "edit": { "*": "deny" },
  "write": { "*": "deny" },
  "task": { "*": "deny" },
  "todowrite": "deny"
}

pre_command:

mkdir -p src && cat > src/a.ts << 'EOF'
import { foo } from 'oldlib';
export const a = foo();
EOF
cat > src/b.ts << 'EOF'
import { bar } from 'newlib';
export const b = bar();
EOF
cat > src/c.ts << 'EOF'
import { baz, qux } from 'oldlib';
import fs from 'fs';
export const c = baz(fs);
export const d = qux();
EOF
cat > src/d.ts << 'EOF'
import path from 'path';
export const e = path.join('/', 'tmp');
EOF
```

### Example 3

```
question: Refactor src/server.js: extract each route handler into its own file under src/routes/, and update src/server.js to just wire them up.

agent_name: solo

agent_content:

---
name: solo
mode: primary
description: Solo coding agent.
---
Accomplish tasks using the tools available to you.

opencode_permissions:

{
  "bash": "allow",
  "read": "allow",
  "edit": "allow",
  "write": "allow",
  "glob": "allow",
  "grep": "allow",
  "task": { "*": "deny" },
  "todowrite": "deny"
}

pre_command:

mkdir -p src && cat > src/server.js << 'EOF'
const express = require('express');
const app = express();
app.use(express.json());

app.get('/health', (req, res) => res.json({ ok: true }));

app.get('/users/:id', (req, res) => {
  res.json({ id: req.params.id, name: 'alice' });
});

app.post('/orders', (req, res) => {
  res.status(201).json({ id: 'ord_1', amount: req.body.amount });
});

app.delete('/orders/:id', (req, res) => {
  res.status(204).end();
});

app.listen(8080);
EOF
cat > package.json << 'EOF'
{ "name": "server", "version": "0.1.0", "dependencies": { "express": "^4.19.2" } }
EOF
```

## Overlap notes

Synthetic functions (`login`, `logout`, `connect`, `disconnect`, `chunk`, `sleep`), synthetic packages (`oldlib`, `newlib`), generic Express server. None overlap with v1 benchmark identifiers.
