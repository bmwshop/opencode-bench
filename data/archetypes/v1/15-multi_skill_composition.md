# Archetype 15 — `multi_skill_composition` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), a single task can require the assistant to **load and apply two or more skills in sequence or in parallel**, weaving their outputs together into a unified artifact. This archetype trains *skill composition* — the meta-pattern of "skill A produces token X; skill B consumes X to produce Y; skill C audits Y" — beyond the single-skill load-and-follow case.

Composition shapes to vary across:

- **2-skill sequential (output → input)** — skill A produces a value the task description says skill B will consume. The assistant must run A first, capture A's output, then invoke B with that output as context.
- **2-skill independent (parallel)** — both skills produce parts of the deliverable, no data dependency between them. The assistant can dispatch both, then merge.
- **3-skill chain** — A → B → C, each consuming the previous output.
- **3-skill DAG** — A and B run independently, C consumes the outputs of both.
- **Prose chain (no explicit "first/then")** — the user describes a goal that decomposes into multiple skills naturally, but the prompt does not enumerate them step-by-step. The assistant must recognise the decomposition.
- **Selectivity-with-composition** — the workspace contains 4-5 skills; the assistant must pick the 2-3 actually relevant to the task and ignore the others (rejecting tempting-but-wrong distractors).

The deliverable is typically a single multi-section artifact (`report.md`, `audit.md`, etc.) where each section is sourced from a different skill's output, with explicit cross-references (e.g. "the audit token from `health-check` must appear in the `dep-summary` output"). The grader checks: (a) the right skills were invoked; (b) the artifact contains all required sections; (c) cross-skill data flow is preserved.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the user's request, naturally decomposing into 2-3 skill invocations. May be explicit ("first run the X skill, then the Y skill") or implicit ("write a comprehensive report covering A, B, and C" where A/B/C each have a matching skill).
- `"composition_shape"`: string — one of `"sequential_2"`, `"independent_2"`, `"chain_3"`, `"dag_3"`, `"prose_chain"`, `"selectivity"`. Describes the topology.
- `"skills"`: object — maps each skill name to a `{"skill_md": str, "skill_scripts": object}` pair. Include 2-5 skills; for `"selectivity"` shape, include 1-2 distractor skills the assistant must NOT invoke.
- `"expected_invocations"`: array of strings — the names of skills the assistant must invoke (subset of `skills`'s keys, in the order they should run).
- `"expected_output_path"`: string — the artifact file path (e.g. `"comprehensive_report.md"`).
- `"expected_sections"`: array of strings — required section markers in the artifact (e.g. `["## Validation", "## Review"]`); used by the grader as `file_regex` checks.
- `"cross_references"`: array of strings — substrings from one skill's output that must appear in a section sourced from another skill (e.g. an audit token from skill A must appear in skill B's section).
- `"pre_command"`: string — bash to materialize the project the skills operate on.

## Examples (3)

### Example 1 (sequential_2 — health-check then dep-summary)

```
question: First, run a health check on this microservice (use the health-check skill — it produces a single status token). Then write the health output to health_output.md including a `# TODO: investigate this token` line. Finally, produce a dep-summary report at the repo root that quotes the health token and summarises the project's dependencies. The project ships skills for both steps; use both.

composition_shape: sequential_2

skills:

{
  "health-check": {
    "skill_md": "---\nname: health-check\ndescription: Run a health check on the project. Use when asked to health-check, smoke-check, or sanity-verify the service.\n---\nRun `bash scripts/healthcheck.py`. Capture its stdout. The script prints a single line of the form `STATUS_<8 hex chars>` — that's the health token. Report the token to the user as `status token: STATUS_<token>`.\n",
    "skill_scripts": {
      "scripts/healthcheck.py": "#!/usr/bin/env python3\nimport hashlib\nh = hashlib.sha256(b'health-2026-04').hexdigest()[:8]\nprint(f'STATUS_{h}')\n"
    }
  },
  "dep-summary": {
    "skill_md": "---\nname: dep-summary\ndescription: Summarise package dependencies. Use when asked to review, summarise, or audit project dependencies.\n---\nFor each declared dependency in package.json (or requirements.txt if Python), produce one entry in `dep_summary.md` with this format:\n\n```\n# Dependency summary: <project>\n## Dependencies\n- <name> @ <version> — <one-line note on why it matters>\n```\n\nQuote any context tokens (status tokens, audit tokens) that the user supplies, verbatim.\n",
    "skill_scripts": {}
  }
}

expected_invocations: ["health-check", "dep-summary"]

expected_output_path: dep_summary.md

expected_sections: ["# Dependency summary:", "## Dependencies"]

cross_references: ["STATUS_"]

pre_command:

mkdir -p .opencode/skills && cat > package.json << 'EOF'
{
  "name": "demo-svc",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.19.2",
    "pg": "^8.12.0"
  }
}
EOF
```

### Example 2 (dag_3 — three independent inputs, one combined report)

```
question: Produce a project_report.md at the repo root that combines three things: (1) the health token of this service (use the health-check skill); (2) the number of routes registered in app.py (use the route-count skill); (3) a TODO-focused review of app.py (use the audit-todos skill). Use all three skills to gather the inputs.

composition_shape: dag_3

skills:

{
  "health-check": {
    "skill_md": "---\nname: health-check\ndescription: Run a health check on the project.\n---\nRun `bash scripts/healthcheck.py` and capture the `STATUS_<hex>` token from stdout.\n",
    "skill_scripts": {
      "scripts/healthcheck.py": "#!/usr/bin/env python3\nprint('STATUS_a8c9f1e2')\n"
    }
  },
  "route-count": {
    "skill_md": "---\nname: route-count\ndescription: Count the registered routes in a Flask/Express-style file.\n---\nRun `bash scripts/route_count.py <file>` and capture the count from stdout. Report as `route_count=<n>`.\n",
    "skill_scripts": {
      "scripts/route_count.py": "#!/usr/bin/env python3\nimport sys, re\ntext = open(sys.argv[1]).read()\nn = len(re.findall(r'@app\\.(?:get|post|put|delete)\\(', text))\nprint(f'route_count={n}')\n"
    }
  },
  "audit-todos": {
    "skill_md": "---\nname: audit-todos\ndescription: TODO-focused source audit.\n---\nList each TODO line with `Line <n>: <text>`.\n",
    "skill_scripts": {}
  }
}

expected_invocations: ["health-check", "route-count", "audit-todos"]

expected_output_path: project_report.md

expected_sections: ["^## .*[Hh]ealth", "^## .*[Rr]oute", "^## .*[Tt]odo"]

cross_references: ["STATUS_", "route_count="]

pre_command:

mkdir -p .opencode/skills && cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

# TODO: tune the rate-limiter for v2

@app.get('/health')
def health(): return {"ok": True}

@app.post('/items')
def add_item(): return {"id": 1}

@app.get('/items/<id>')
def get_item(id): return {"id": id}
EOF
```

### Example 3 (selectivity — 5 skills present, only 2 relevant)

```
question: Audit app.py: produce a one-paragraph review that quotes any TODO lines verbatim, and at the end, list the 4 rate-limit configuration constants and their values.

composition_shape: selectivity

skills:

{
  "audit-todos": {
    "skill_md": "---\nname: audit-todos\ndescription: TODO-focused source audit. Use when asked to audit, review, or surface outstanding work items in a Python file.\n---\nFor each TODO line in the target file, quote it verbatim with its line number.\n",
    "skill_scripts": {}
  },
  "rate-limit-extract": {
    "skill_md": "---\nname: rate-limit-extract\ndescription: Extract rate-limit configuration constants from a service file.\n---\nIdentify all module-level constants whose names look like rate-limit knobs (`RL_*`, `*_RATE_LIMIT`, `*_BURST`, `*_WINDOW_SEC`). Report each as `<NAME>=<value>`.\n",
    "skill_scripts": {}
  },
  "health-check": {
    "skill_md": "---\nname: health-check\ndescription: Run a health check on the service. Use only when explicitly asked to health-check or smoke-check the service.\n---\nRun the health-check script and report its token.\n",
    "skill_scripts": {
      "scripts/healthcheck.py": "#!/usr/bin/env python3\nprint('STATUS_a8c9f1e2')\n"
    }
  },
  "release-tag": {
    "skill_md": "---\nname: release-tag\ndescription: Cut a release tag. Use only when explicitly asked to tag, release, or publish.\n---\nRun the release script with the target version.\n",
    "skill_scripts": {
      "scripts/release.sh": "#!/bin/bash\necho 'RELEASE_ID=rel_1'\n"
    }
  },
  "log-rotate": {
    "skill_md": "---\nname: log-rotate\ndescription: Rotate the service's log files. Use only when explicitly asked to rotate, archive, or clean up logs.\n---\nMove old logs to logs/archive/ and truncate the active log.\n",
    "skill_scripts": {}
  }
}

expected_invocations: ["audit-todos", "rate-limit-extract"]

expected_output_path: audit_report.md

expected_sections: ["TODO", "RL_PER_SEC", "RL_BURST"]

cross_references: []

pre_command:

mkdir -p .opencode/skills && cat > app.py << 'EOF'
# TODO: tune the rate-limiter for v2
# TODO: switch backend to redis-cell

RL_PER_SEC = 100
RL_BURST = 200
RL_WINDOW_SEC = 60
RL_PENALTY_SEC = 300

def handle(req): pass
EOF
```

## Overlap notes

Skill names used: `health-check`, `dep-summary`, `route-count`, `audit-todos`, `rate-limit-extract`, `release-tag`, `log-rotate`. **None** of these match v1 benchmark skill names (`review-flow`, `audit-flow`, `summary-flow`, `validate-train`, `count-imports`, `compute-checksum`, `naming-convention`, `api-style`, `encoding-convention`, `parallel-3-facet-audit`, `chain-read-grep-edit`, `dag-two-inputs-one-output`, `iter-def-count`, `iter-helper-callers`, `code-review`, `python-review`, `super-review`, `todo-review`, `parallel-2-module-compare`, `dag-response-attrs`, `chain-extract-check-report`, `xyz-001`).

Project fixtures use synthetic names:

- `app.py` (a Flask service, not the benchmark's `train.py`)
- `package.json` for dep summary
- `STATUS_<hex>` token (not the benchmark's `VALID_<hex>`)
- `route_count=<n>` (not the benchmark's `import_count=<n>`)
- `RL_PER_SEC` / `RL_BURST` constants (not the benchmark's `EMBEDDING_LR` / `WEIGHT_DECAY`)

The composition topology (`sequential_2`, `dag_3`, `selectivity`) mirrors the v1 benchmark's skill Tier D/E shape, but every concrete name is distinct to avoid contaminating the eval.