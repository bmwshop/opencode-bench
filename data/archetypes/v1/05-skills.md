# Archetype 05 — `skills`

## Description

In OpenCode (an agentic CLI similar to Claude Code), a 'skill' is a packaged workflow under `.opencode/skills/<name>/SKILL.md` (plus optional helper files). Registered skills appear in the assistant's `skill` tool's available_skills list with their descriptions; calling `skill(name='<name>')` returns the SKILL.md body, which the assistant then follows.

Skills come in several SHAPES — pick whichever fits the scenario:

1. **Script runner** — SKILL.md tells the assistant to run an included executable (`deploy.sh`, `bench.sh`, `lint.sh`) and parse its output.
2. **Procedural workflow (no scripts)** — SKILL.md is an ordered checklist the assistant carries out using its own tools (e.g. 'incident-postmortem': read `logs/`, identify error window, open the named module, fill in this report template). `skill_scripts` is empty.
3. **Reference / knowledge (no scripts)** — SKILL.md is a reference document the assistant should apply (e.g. 'git-conventions': commit format, branch naming; 'stripe-integration': canonical patterns to use). `skill_scripts` is empty.
4. **Templates** — SKILL.md + template files (`Dockerfile.template`, `github-action.yml`, sql-migration skeleton) — the assistant uses them to scaffold something. Templates in `skill_scripts` must use placeholders or skeletons — they're starting points the assistant fills in, not the finished outputs.
5. **Multi-tool chain** — SKILL.md describes a small workflow combining bash/read/edit (e.g. 'release-notes': git log → group by type → write CHANGELOG.md). May or may not include helper scripts.

The user asks naturally about the skill's topic (does NOT need to mention the skill explicitly — the assistant matches semantically).

## Output fields

Output a JSON object with these fields:

- `"question"`: string — natural user phrasing that matches the skill's topic.
- `"skill_name"`: string — short lowercase name (e.g. `"deploy"`, `"incident-postmortem"`, `"git-conventions"`).
- `"skill_md"`: string — content for SKILL.md. YAML frontmatter (`name`, `description` that appears in the tools section) plus a body the assistant follows.
- `"skill_scripts"`: object — maps filename to file content for any helper files. CAN BE EMPTY (`{}`) for procedural-workflow or reference-knowledge skills.
- `"pre_command"`: string — bash to create project files the skill operates on; empty for from-scratch tasks.

## Examples (3)

### Example 1

```
question: Deploy the latest build to staging and let me know the deploy ID.

skill_name: deploy

skill_md:

---
name: deploy
description: Deployment workflow. Use when asked to deploy to any environment (dev, staging, prod).
---
To run a deploy:

1. Run `./deploy.sh <environment>`; default is `staging`.
2. The script runs migrations, builds, and pushes. Look for a line starting with `DEPLOY_ID=` and another starting with `STATUS=`.
3. Report both the deploy ID and the status to the user.

skill_scripts:

{
  "deploy.sh": "#!/bin/bash\nenv=${1:-staging}\necho \"Running migrations for $env...\"\nsleep 0\necho \"Building image...\"\nsleep 0\necho \"Pushing to registry...\"\necho \"DEPLOY_ID=dep_${env}_$(date +%s)\"\necho \"STATUS=SUCCESS\"\n"
}

pre_command: ``
```

### Example 2

```
question: We had a P1 last night around 02:00 UTC. Can you put together the postmortem? Logs are in logs/ and the recent commits should give the context.

skill_name: incident-postmortem

skill_md:

---
name: incident-postmortem
description: Incident postmortem workflow. Use when asked to write up or investigate a production incident.
---
Follow this workflow exactly:

1. Read all files under `logs/`. Identify the time window of the incident (look for ERROR / FATAL lines and a sudden burst of warnings).
2. Run `git log --since='24 hours ago' --oneline` to list commits that landed in the relevant window. Read the diffs for any that touched the modules referenced in the error logs.
3. Identify the most likely root cause. Cite the specific log line(s) and commit(s) that support your conclusion.
4. Produce a postmortem document with EXACTLY these sections, in this order:
   - Background — what the system does, what was happening before the incident.
   - Impact — who/what was affected and for how long.
   - Detection — how the issue was first noticed.
   - Root cause — your conclusion with citations.
   - Remediation — what was (or should be) done to recover.
   - Prevention — concrete follow-up items so it doesn't recur.
5. Save the document to `postmortem.md` in the project root.

skill_scripts:

{}

pre_command:

mkdir -p logs && cat > logs/api.log << 'EOF'
2026-04-23T01:55:14Z INFO  startup version=1.4.2
2026-04-23T01:58:02Z INFO  health ok
2026-04-23T02:01:11Z WARN  db pool exhausted, queue=42
2026-04-23T02:01:12Z WARN  db pool exhausted, queue=88
2026-04-23T02:01:13Z ERROR handler=POST /api/orders error="context deadline exceeded"
2026-04-23T02:01:14Z ERROR handler=POST /api/orders error="context deadline exceeded"
2026-04-23T02:01:15Z FATAL panic in http.Serve, restarting
2026-04-23T02:03:40Z INFO  startup version=1.4.2
2026-04-23T02:03:55Z INFO  health ok
EOF
cat > logs/db.log << 'EOF'
2026-04-23T02:01:10Z INFO connections=49/50
2026-04-23T02:01:11Z WARN connections=50/50 — refusing new
2026-04-23T02:01:30Z WARN slow query 4.2s SELECT * FROM orders WHERE user_id = $1
2026-04-23T02:01:30Z WARN slow query 4.4s SELECT * FROM orders WHERE user_id = $1
EOF
```

### Example 3

```
question: I'm about to commit some changes — what's our convention here and what should the commit look like?

skill_name: git-conventions

skill_md:

---
name: git-conventions
description: Project git and commit conventions. Use when asked about commit messages, branch names, or PR rules.
---
## Commit message format

Every commit follows: `type(scope): short subject`

- type: one of `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `build`, `ci`
- scope: optional, kebab-case, names the affected area (e.g. `auth`, `cli`, `db`)
- subject: imperative mood, no trailing period, ≤ 72 chars

Body (optional, separated by a blank line) wrapped at 72 chars; explain the WHY.

Footer (optional): `BREAKING CHANGE: <description>` or `Refs: #123`.

## Branch names

`<type>/<short-kebab-description>`, e.g. `feat/auth-jwt-rotation`, `fix/cli-help-text`.

## PR rules

- Squash-merge only.
- The PR title becomes the squash commit subject — must follow the commit format.
- Body of the PR fills in the commit body.
- Every PR must pass CI before review.

When the user asks about committing, refresh these rules in your head and tailor the suggested message to whatever they're committing.

skill_scripts:

{}

pre_command:

git init -q . 2>/dev/null && mkdir -p src && cat > src/auth.ts << 'EOF'
export function rotateKey() { /* TODO */ }
EOF
git add -A 2>/dev/null && git -c user.email=dev@example.com -c user.name=dev commit -q -m 'initial commit' 2>/dev/null || true
```

## Overlap notes

Skill names (`deploy`, `incident-postmortem`, `git-conventions`) do not collide with any v1 benchmark skill names (which include `review-flow`, `audit-flow`, `summary-flow`, `validate-train`, `count-imports`, `compute-checksum`, `naming-convention`, `api-style`, `encoding-convention`, `parallel-3-facet-audit`, `chain-read-grep-edit`, `dag-two-inputs-one-output`, `iter-def-count`, `iter-helper-callers`, `code-review`, `python-review`, `super-review`, `todo-review`, `parallel-2-module-compare`, `dag-response-attrs`, `chain-extract-check-report`, `xyz-001`). Project fixtures are synthetic.
