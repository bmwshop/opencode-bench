# Archetype 10 — `tool_restriction_prompt`

## Description

In OpenCode (an agentic CLI similar to Claude Code), a custom primary agent's system prompt can instruct the assistant to use only a subset of its tools. All tools STILL appear in the assistant's tool schema — the constraint is enforced by the agent prompt alone.

Common restriction patterns:

- **bash-only** — use only the `bash` tool, no `read`/`edit`/`write`/`glob`/`grep`/`task`
- **read-only** — use only `read`/`glob`/`grep` (and `bash` for inspection); no `edit`/`write`
- **no-bash** — use the specialised tools (`read`/`write`/`edit`/`glob`/`grep`) but never run shell commands
- **write-once** — read freely but never edit existing files; only create new ones via `write`
- **inspect-only** — use only `read` and `grep`; no `glob`, no `bash`, no edits
- **search-only** — use only `grep` and `glob`; no reading file contents directly

Pick a restriction; the user's request is a normal coding/search task the assistant must complete within that restriction.

The agent's tool restriction lives in `agent_content` and is the assistant's responsibility to follow — the user's `question` shouldn't restate it. A real developer's question describes their development task, not the agent's tool config. Natural mentions of preferences are fine ("just review, don't change anything" is OK with a read-only agent); parroting the agent's enumerated tools verbatim ("without using bash", "using only grep and glob") is not.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — a normal coding or search task.
- `"agent_name"`: string — kebab-case agent name (e.g. `"bash-only"`, `"read-only"`, `"no-bash"`).
- `"agent_content"`: string — agent markdown with YAML frontmatter (`mode: "primary"`). Body explicitly states which tool(s) are allowed and which are forbidden.
- `"pre_command"`: string — bash to create files for the task.

## Examples (3)

### Example 1

```
question: Find which file under src/ defines the MIGRATION_ID constant and print its value.

agent_name: bash-only

agent_content:

---
name: bash-only
mode: primary
description: Agent restricted to the bash tool.
---
You may only use the bash tool. Do not use read, edit, write, glob, grep, task, or any other tool. Use shell commands for everything.

pre_command:

mkdir -p src/migrations src/api && cat > src/api/server.ts << 'EOF'
import express from 'express';
const app = express();
app.listen(8080);
EOF
cat > src/migrations/001.ts << 'EOF'
import fs from 'fs';
export const MIGRATION_ID = 'm_2024_11_08_orders_index';
export async function up(db: any) { await db.query('CREATE INDEX ...'); }
EOF
cat > src/migrations/002.ts << 'EOF'
export async function up(db: any) { await db.query('ALTER TABLE ...'); }
EOF
```

### Example 2

```
question: Investigate why our CI is suddenly twice as slow. Look at the workflow file and the build scripts and tell me where the time is being spent.

agent_name: read-only

agent_content:

---
name: read-only
mode: primary
description: Read-only investigation agent. May read, search, and inspect — never modifies anything.
---
You may only use these tools: read, glob, grep, and bash for read-only inspection (e.g. `cat`, `ls`, `find`, `wc`, `head`, `tail`, `grep`). You must NEVER use edit, write, or any bash command that modifies files (`cp`, `mv`, `rm`, `>`, `>>`, `sed -i`, `tee`, etc.). If a task seems to require changes, describe them in your response but do NOT carry them out.

pre_command:

mkdir -p .github/workflows scripts && cat > .github/workflows/ci.yml << 'EOF'
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --runInBand --coverage
      - run: npm run build
      - run: bash scripts/integration.sh
      - run: bash scripts/upload-artifacts.sh
EOF
cat > scripts/integration.sh << 'EOF'
#!/usr/bin/env bash
set -e
for i in $(seq 1 50); do
  npm run test:e2e -- --grep "smoke-$i"
done
EOF
cat > scripts/upload-artifacts.sh << 'EOF'
#!/usr/bin/env bash
set -e
for f in dist/*.tar.gz; do
  curl -F "file=@$f" https://artifacts.example.com/upload || true
  sleep 5
done
EOF
```

### Example 3

```
question: Add a formatDate(d: Date): string function to src/utils.ts that returns the date in ISO-8601 (YYYY-MM-DD) format.

agent_name: no-bash

agent_content:

---
name: no-bash
mode: primary
description: Coding agent that uses the file tools but never the shell.
---
You may use read, write, edit, glob, and grep. You may NEVER use the bash tool — no shell commands, no `npm`, no `python`, no `git`. If verification is needed, do it by reading the file you just wrote.

pre_command:

mkdir -p src && cat > src/utils.ts << 'EOF'
export function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

export function chunk<T>(a: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < a.length; i += size) out.push(a.slice(i, i + size));
  return out;
}
EOF
```

## Overlap notes

Synthetic constants and functions (`MIGRATION_ID`, `formatDate`, `clamp`, `chunk`). The "investigate slow CI" example uses a synthetic GitHub workflow + synthetic shell scripts. None overlap with v1 benchmark identifiers.
