# Archetype 08 — `sequential_tool_use`

## Description

A request that requires 2-4 tool calls in a SPECIFIC ORDER, where each step depends on or follows the previous one. Vary the combinations across samples:

- `read → edit` (read a file, change something specific based on its contents)
- `grep → read → edit` (find references, open one, change it)
- `glob → read → write` (list files, read one, write a derived file)
- `grep → read` (find pattern, then read full file for understanding)
- `read → write` (read one file, write a derived/transformed file)
- `bash → read → edit` (run a command, read its output, edit a file based on it)

Each step should genuinely depend on the previous step's result.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — implies an ordered workflow.
- `"pre_command"`: string — bash to create files with enough content for each step to be meaningful.

## Examples (3)

### Example 1

```
question: Read src/utils.ts, then change the TOKEN value from "abc123" to "xyz789".

pre_command:

mkdir -p src && cat > src/utils.ts << 'EOF'
export const TOKEN = "abc123";
export const TIMEOUT = 5000;
EOF
```

### Example 2

```
question: Find which file in src/ defines the function processOrder, then read it to see the current timeout, then change that timeout from 5000 to 30000.

pre_command:

mkdir -p src && cat > src/server.ts << 'EOF'
import express from 'express';
const app = express();
app.listen(8080);
EOF
cat > src/orders.ts << 'EOF'
export async function processOrder(items: any[]): Promise<{ id: string }> {
  const TIMEOUT = 5000;
  await new Promise(r => setTimeout(r, 0));
  return { id: 'ord_' + Date.now() };
}

export function listOrders() { return []; }
EOF
cat > src/users.ts << 'EOF'
export function getUser(id: string) { return { id, name: 'alice' }; }
EOF
```

### Example 3

```
question: Look across the TypeScript files in src/, find which file uses the deprecated oldFunction() the most times, open that file, and replace every oldFunction() call there with newFunction().

pre_command:

mkdir -p src && cat > src/auth.ts << 'EOF'
import { oldFunction } from './deprecated';

export function login(user: string) {
  return oldFunction(user);
}
EOF
cat > src/orders.ts << 'EOF'
import { oldFunction } from './deprecated';

export function processOrder(id: string) {
  const a = oldFunction(id);
  const b = oldFunction(id + '_meta');
  const c = oldFunction(id + '_audit');
  return { a, b, c };
}
EOF
cat > src/users.ts << 'EOF'
export function listUsers() {
  return [];
}
EOF
cat > src/deprecated.ts << 'EOF'
export function oldFunction(x: string): string { return x.toUpperCase(); }
export function newFunction(x: string): string { return x.toUpperCase(); }
EOF
```

## Overlap notes

Synthetic functions (`processOrder`, `oldFunction`, `newFunction`, `login`) and synthetic constants (`TOKEN`, `TIMEOUT`) only. No collision with benchmark identifiers.
