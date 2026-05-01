# Archetype 15 — `multi_skill_composition` (NEW)

## Description

In OpenCode (an agentic CLI similar to Claude Code), a single task can require the assistant to **load and apply two or more skills**, weaving their outputs together — or to **discriminate between candidate skills** in a workspace, picking only the relevant ones (or none, if no skill applies). This archetype trains the *multi-skill* end of the skill family: composition (Tier E) and selectivity (Tier D) shapes.

The benchmark v1 `skill` family (#401–#430) splits into 5 internal tiers:

| Tier | description | n samples | covered by archetype |
|---|---|---|---|
| A — baseline | load and follow a single explicit skill | 9 (#401–#409) | archetype 05 (`skills`) |
| B — discovery | discover the right skill from a 2- to 5-skill catalog | 5 (#410–#414) | archetype 05 |
| C — recipe | single skill prescribes a parallel/chain/dag/iter execution | 8 (#415–#422) | archetype 05 |
| **D — selectivity** | pick the right skill (or NONE) from confusable distractors | **4 (#423–#426)** | **this archetype** |
| **E — composition** | combine 2–3 skills (sequential / independent / chain / DAG / prose-chain) | **4 (#427–#430)** | **this archetype** |

So this archetype's territory is **8 of 30 skill samples (27%)** — the multi-skill end. Single-skill load-and-follow patterns (Tiers A/B/C) are archetype 05's job.

Composition shapes the benchmark uses:

- **`sequential_2`** — skill A produces a value the task description says skill B will consume. Run A first, capture its output, then invoke B with that output as context. (Benchmark: `composition-2-sequential` = #427)
- **`independent_2`** — both skills produce parts of the deliverable, **no data dependency** between them. Both can be dispatched concurrently. (Benchmark: `composition-2-independent` = #428)
- **`prose_chain`** — the user describes a goal in natural prose **without enumerating** "first/then/finally". The assistant must recognise the multi-skill decomposition implicitly. (Benchmark: `composition-prose-chain` = #429)
- **`dag_3`** — three skills run with at least one converging step (e.g. A and B independent, C consumes both). (Benchmark: `composition-3-skills` = #430)

Selectivity shapes:

- **`selectivity_pool`** — workspace has 4–5 skills with overlapping descriptions; pick the right one(s). (Benchmark: `selectivity-pool-of-5` = #423; also `-language` = #425, `-vocab-pollution` = #426)
- **`selectivity_no_match`** — workspace has 3–5 plausible-looking skills, but **none** actually applies to the user's task. The model must invoke NONE and produce a calibrated refusal. (Benchmark: `selectivity-no-match-plausible` = #424)

The deliverable is typically a single multi-section artifact (`report.md`, `audit.md`, etc.) where each section is sourced from a different skill's output, with explicit cross-references. The grader checks: (a) the right skills were invoked (or that NO skills were invoked, for `selectivity_no_match`); (b) the artifact contains all required sections; (c) cross-skill data flow is preserved where applicable.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — the user's request, naturally decomposing into 1–3 skill invocations (or zero, for `selectivity_no_match`). May be explicit ("first run the X skill, then the Y skill") or implicit ("write a comprehensive report covering A, B, and C" where A/B/C each have a matching skill).
- `"composition_shape"`: string — one of `"sequential_2"`, `"independent_2"`, `"prose_chain"`, `"dag_3"`, `"selectivity_pool"`, `"selectivity_no_match"`. Describes the topology.
- `"skills"`: object — maps each skill name to a `{"skill_md": str, "skill_scripts": object}` pair. Include 2–5 skills; for `selectivity_*` shapes, include 1–4 distractor skills the assistant must NOT invoke.
- `"expected_invocations"`: array of strings — the names of skills the assistant must invoke (subset of `skills`'s keys, in the order they should run). **Empty array `[]` for `selectivity_no_match`.**
- `"expected_output_path"`: string — the artifact file path (e.g. `"report.md"`).
- `"expected_sections"`: array of strings — required section markers in the artifact (e.g. `["## Validation", "## Review"]`); used by the grader as `file_regex` checks. For `selectivity_no_match`, this typically contains a refusal phrase.
- `"cross_references"`: array of strings — substrings from one skill's output that must appear in a section sourced from another skill. Empty for `independent_2`, `selectivity_*`, and any non-data-dependency shape.
- `"pre_command"`: string — bash to materialize the project the skills operate on.

## Examples (6)

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

### Example 2 (dag_3 — three skills, one combined report)

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

### Example 3 (selectivity_pool — 5 skills present, only 2 relevant)

```
question: Audit app.py: produce a one-paragraph review that quotes any TODO lines verbatim, and at the end, list the 4 rate-limit configuration constants and their values.

composition_shape: selectivity_pool

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

### Example 4 (independent_2 — two skills, no data dependency)

```
question: Produce a `pipeline_status.md` at the repo root with two sections, in this order:

  ## Build
  <output of the build-status skill>

  ## Coverage
  <output of the coverage-summary skill>

The two sections are independent — each summarises a separate concern, neither feeds into the other.

composition_shape: independent_2

skills:

{
  "build-status": {
    "skill_md": "---\nname: build-status\ndescription: Report the latest build status of the project.\n---\nRun `bash scripts/build_status.sh`. Capture its stdout — a single line of the form `BUILD_<status>` (e.g. `BUILD_OK` or `BUILD_FAIL`). Report it as the body of the build section.\n",
    "skill_scripts": {
      "scripts/build_status.sh": "#!/bin/bash\necho 'BUILD_OK'\n"
    }
  },
  "coverage-summary": {
    "skill_md": "---\nname: coverage-summary\ndescription: Report the latest test-coverage percentage.\n---\nRun `bash scripts/coverage.sh`. Capture its stdout — a single line of the form `COVERAGE_<pct>` (e.g. `COVERAGE_87`). Report it as the body of the coverage section.\n",
    "skill_scripts": {
      "scripts/coverage.sh": "#!/bin/bash\necho 'COVERAGE_87'\n"
    }
  }
}

expected_invocations: ["build-status", "coverage-summary"]
expected_output_path: pipeline_status.md
expected_sections: ["^## Build", "^## Coverage", "BUILD_OK", "COVERAGE_87"]
cross_references: []

pre_command:

mkdir -p .opencode/skills && touch .gitkeep
```

### Example 5 (prose_chain — implicit decomposition from natural goal)

```
question: I'm preparing the weekly status note for the on-call rotation. Help me put together a one-page summary that tells the team whether the service is healthy right now and what work items are still outstanding in the main entry point. Drop it in `oncall_status.md` at the repo root.

composition_shape: prose_chain

skills:

{
  "health-check": {
    "skill_md": "---\nname: health-check\ndescription: Run a health check on the service. Use when asked about service health, deployment safety, or smoke-test status.\n---\nRun `bash scripts/healthcheck.py`. Capture the `STATUS_<hex>` token from stdout. Report it.\n",
    "skill_scripts": {
      "scripts/healthcheck.py": "#!/usr/bin/env python3\nprint('STATUS_b3f1c0a4')\n"
    }
  },
  "audit-todos": {
    "skill_md": "---\nname: audit-todos\ndescription: TODO-focused source audit. Use when asked about outstanding work, pending action items, or unresolved follow-ups in a source file.\n---\nList each TODO line in the target file with `Line <n>: <text>`.\n",
    "skill_scripts": {}
  }
}

expected_invocations: ["health-check", "audit-todos"]
expected_output_path: oncall_status.md
expected_sections: ["[Ss]ervice [Hh]ealth", "[Tt]odo|[Oo]utstanding|[Pp]ending"]
cross_references: ["STATUS_b3f1c0a4"]

pre_command:

mkdir -p .opencode/skills && cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

# TODO: add rate-limit metrics endpoint
# TODO: deprecate /v0 routes

@app.get('/health')
def health(): return {"ok": True}
EOF
```

### Example 6 (selectivity_no_match — calibrated refusal, no skill applies)

```
question: Translate the README.md in this repo into French. Just produce the translated text in `README.fr.md` at the repo root.

composition_shape: selectivity_no_match

skills:

{
  "build-status": {
    "skill_md": "---\nname: build-status\ndescription: Report the latest build status of the project. Use only when asked about build, CI, or compilation status.\n---\nRun `bash scripts/build_status.sh` and report the BUILD_<status> token.\n",
    "skill_scripts": {
      "scripts/build_status.sh": "#!/bin/bash\necho 'BUILD_OK'\n"
    }
  },
  "audit-todos": {
    "skill_md": "---\nname: audit-todos\ndescription: TODO-focused source audit. Use only when asked to surface outstanding work items in a source file.\n---\nList each TODO line.\n",
    "skill_scripts": {}
  },
  "release-tag": {
    "skill_md": "---\nname: release-tag\ndescription: Cut a release tag. Use only when explicitly asked to tag, release, or publish.\n---\nRun the release script.\n",
    "skill_scripts": {
      "scripts/release.sh": "#!/bin/bash\necho 'RELEASE_ID=rel_1'\n"
    }
  }
}

expected_invocations: []
expected_output_path: README.fr.md
expected_sections: []
cross_references: []

pre_command:

mkdir -p .opencode/skills && cat > README.md << 'EOF'
# demo-svc

A small demonstration service.

## Usage

Run `python app.py` to start the service on port 8080.
EOF
```

In the `selectivity_no_match` case, the grader checks that **none of the available skills was invoked** (via `no_tool_param_value_recursive` against each skill name) and that the deliverable was produced by the model directly (e.g., the model translates the README itself, since none of the skills offer translation). The model must recognise the no-match condition and proceed without false skill activation. Generators producing such samples should ensure the workspace skills are *plausibly tempting* but actually irrelevant — that's the whole test.

## Distribution targets (mirror v1 `skill` Tier D + E)

| axis | benchmark (Tier D + E) | this archetype (6 examples) |
|---|---|---|
| **composition shape** — sequential_2 / independent_2 / prose_chain / dag_3 / selectivity_pool / selectivity_no_match | 1/1/1/1/1+2/1 (each ≈ 12.5%) | 1/1/1/1/1/1 (one of each, ~17%) |
| **scope_kind** — multi-skill-invocation / multi-skill-workspace | 4/4 (composition vs selectivity) | 4 composition / 2 selectivity (1 pool, 1 no-match) |
| **expected invocation count** — 0 / 2 / 3 / 5 | 1 / 3 / 4 / 0 | 1 (no-match) / 3 (sequential, independent, prose-chain) / 1 (dag_3) / 1 (pool-of-5) |

The 6 examples cover all 6 distinct sub-shapes the benchmark tests for Tiers D + E. Generators may extend with additional `selectivity_pool` variants (`-language`, `-vocab-pollution`) — those follow the same `selectivity_pool` pattern with different distractor types and the archetype's existing example covers the meta-pattern.

## Overlap notes

Skill names used: `health-check`, `dep-summary`, `route-count`, `audit-todos`, `rate-limit-extract`, `release-tag`, `log-rotate`, `build-status`, `coverage-summary`. **None** of these match v1 benchmark skill names (`review-flow`, `audit-flow`, `summary-flow`, `validate-train`, `count-imports`, `compute-checksum`, `naming-convention`, `api-style`, `encoding-convention`, `parallel-3-facet-audit`, `chain-read-grep-edit`, `dag-two-inputs-one-output`, `iter-def-count`, `iter-helper-callers`, `code-review`, `python-review`, `super-review`, `todo-review`, `parallel-2-module-compare`, `dag-response-attrs`, `chain-extract-check-report`, `xyz-001`).

Project fixtures use synthetic names:

- `app.py` (a Flask service, not the benchmark's `train.py`)
- `package.json` for dep summary
- `STATUS_<hex>` and `BUILD_OK` / `COVERAGE_87` tokens (not the benchmark's `VALID_<hex>`)
- `route_count=<n>` (not the benchmark's `import_count=<n>`)
- `RL_PER_SEC` / `RL_BURST` constants (not the benchmark's `EMBEDDING_LR` / `WEIGHT_DECAY`)
- README translation as the no-match scenario

The composition topologies (`sequential_2`, `dag_3`, `independent_2`, `prose_chain`, `selectivity_pool`, `selectivity_no_match`) mirror the v1 benchmark's skill Tier D + E sub-shapes 1-to-1, but every concrete name is distinct to avoid contaminating the eval.
