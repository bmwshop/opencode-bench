# v1 #424 skill_selectivity_no_match_plausible

## Category

skill (delivery: `.opencode/skills/<name>/SKILL.md`)

## Structural signature

- template: **selectivity-no-match-plausible**
- scope_kind: **multi-skill-workspace**
- answer_shape: **tool-presence-or-absence**
- unique_trait: 3 plausibly-relevant skills (vocabulary overlap); none actually fit; model should solve manually

## Repo

`requests` (pinned via `data/v1_repos.json`).

## Skills installed (workspace overlay)

### `train-validator`

`projects/v1/skills/424/.opencode/skills/train-validator/SKILL.md`:

```text
---
name: train-validator
description: Validate the training pipeline (autoresearch). Runs the bundled training-validation script and reports the validation token. Use ONLY for training-pipeline validation.
---

To validate the training pipeline, run `scripts/validate.py` and report the
captured `VALID_<hex>` token. This skill is specific to training-pipeline
validation; it does NOT cover general file analysis or summarization.
```

### `lint-runner`

`projects/v1/skills/424/.opencode/skills/lint-runner/SKILL.md`:

```text
---
name: lint-runner
description: Run a Python linter (flake8) and emit a list of style violations. Use ONLY when the user asks for lint output or a style violation report.
---

To run the linter, invoke `flake8` via bash on the target file and report
the resulting violations. This skill produces a violation list; it does
NOT summarize file purpose or describe what the file does.
```

### `security-scanner`

`projects/v1/skills/424/.opencode/skills/security-scanner/SKILL.md`:

```text
---
name: security-scanner
description: Scan a file for common security vulnerabilities (SQL injection, hardcoded credentials, unsafe deserialization). Use ONLY when the user asks for a security audit.
---

To scan for security issues, read the file and check for known dangerous
patterns. This skill produces a vulnerability report; it does NOT produce a
plain-English summary or general overview of the file.
```


## Prompt

> Read `src/requests/utils.py` and write a one-paragraph plain-English summary of the file's purpose to `purpose.md` at the repo root.
> 
> The project has several skills installed; if none of them match this task, just solve it directly with normal tools.

## Pass criteria (5 checks)

| # | type | description |
|---|------|-------------|
| 1 | `no_tool_name_recursive` | model did NOT load any skill (none match the summarization task) |
| 2 | `any_tool_name` | model read the file |
| 3 | `any_tool_name` | model produced the purpose.md artifact |
| 4 | `file_regex` | purpose.md is non-empty |
| 5 | `call_schema_valid` | all tool calls match opencode schemas |

## Note on methodology

This sample is part of v1's SKILL family (#401-#430). The SKILL.md content is a
workspace overlay applied at session start by `run.py`; opencode auto-injects the
skill catalog (name + description + filesystem location) into the system prompt
each turn (see `session/system.ts:65-77` and `skill/index.ts:262-278`). The
catalog is **not** injected into subagents whose permission set has `skill` in
the deny list (notably `explore`), so the family expects all `skill name=X`
invocations at the parent agent layer.

## Authoring notes

Refinement of #414. Distractors share vocabulary with the user task ('validation' / 'check' / 'analyze') but none does file summarization. Pilot data showed #414's distractors were too obviously off-topic (every model passed); these distractors should produce non-trivial discrimination.
