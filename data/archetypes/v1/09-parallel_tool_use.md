# Archetype 09 — `parallel_tool_use`

## Description

A request combining 2-3 INDEPENDENT operations on different files or resources, so the assistant can issue them as multiple tool calls in a SINGLE turn — no data dependency between them. Common combinations:

- `read + read` (two unrelated config files)
- `read + grep` (read one file AND search a different directory)
- `grep + grep` (search two unrelated patterns in two unrelated places)
- `read × 3` (summarise three different config layers at once)
- `read + bash` (read a file AND run a status command)
- `glob + read` (list files AND read an unrelated one)

Phrase the question like a real developer — don't name the assistant's tools unless necessary; the assistant will choose them itself.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — 2-3 independent operations, phrased to invite simultaneous execution ("simultaneously", "at the same time", "both", or a list of separate items).
- `"pre_command"`: string — bash to create the independent files/resources.

## Examples (3)

### Example 1

```
question: Give me a summary of both package.json and jest.config.js at the same time — read them both and tell me what each one configures.

pre_command:

cat > package.json << 'EOF'
{
  "name": "api",
  "version": "1.4.2",
  "scripts": {
    "build": "tsc",
    "test": "jest",
    "lint": "eslint src"
  },
  "dependencies": {
    "express": "^4.19.2",
    "jsonwebtoken": "^9.0.2",
    "pg": "^8.12.0"
  },
  "devDependencies": {
    "typescript": "^5.5.4",
    "jest": "^29.7.0",
    "ts-jest": "^29.2.5"
  }
}
EOF
cat > jest.config.js << 'EOF'
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.test.ts'],
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.d.ts'],
  coverageThreshold: { global: { branches: 70, functions: 80, lines: 80, statements: 80 } },
};
EOF
```

### Example 2

```
question: At the same time: read .env.example so I can see the environment variables we expect, AND grep src/ for any TODO comments. Give me both results together.

pre_command:

cat > .env.example << 'EOF'
DATABASE_URL=postgres://user:pass@localhost:5432/app
REDIS_URL=redis://localhost:6379
JWT_SECRET=change-me
LOG_LEVEL=info
STRIPE_KEY=sk_test_xxx
EOF
mkdir -p src && cat > src/auth.ts << 'EOF'
export function login() {
  // TODO: rate limit
  return true;
}
EOF
cat > src/billing.ts << 'EOF'
export function charge(amt: number) {
  // TODO: validate amt
  // TODO: handle declines properly
  return { id: 'ch_1' };
}
EOF
cat > src/cache.ts << 'EOF'
export class Cache {
  private m = new Map<string, any>();
  get(k: string) { return this.m.get(k); }
  set(k: string, v: any) { this.m.set(k, v); }
}
EOF
```

### Example 3

```
question: Summarise three configs in parallel for me: docker-compose.yml, .github/workflows/ci.yml, and tsconfig.json. Just one short paragraph per file.

pre_command:

mkdir -p .github/workflows && cat > docker-compose.yml << 'EOF'
version: '3.9'
services:
  api:
    build: .
    ports: ['8080:8080']
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/app
      - REDIS_URL=redis://cache:6379
    depends_on: [db, cache]
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
  cache:
    image: redis:7-alpine
EOF
cat > .github/workflows/ci.yml << 'EOF'
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
EOF
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "strict": true,
    "outDir": "dist",
    "rootDir": "src",
    "esModuleInterop": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
EOF
```

## Overlap notes

Synthetic configs only (`package.json`, `jest.config.js`, `.env.example`, `docker-compose.yml`, etc.). No benchmark identifier collisions.
