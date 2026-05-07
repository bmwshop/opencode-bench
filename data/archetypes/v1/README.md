# v1 archetypes — training-data category specifications

This folder contains one markdown spec per *archetype* — a category of training-data sample shapes used by `scripts/generation/create_opencodestyle_categories_input.py` and downstream generators. Each archetype describes:

- The OpenCode mechanism it exercises (system prompt channel, tool surface, agent shape, etc.).
- The breadth of real-world scenarios that fit the archetype.
- The exact JSON output schema the question-generator is expected to emit.
- 3–6 worked examples illustrating the archetype.

## Layout

```
data/archetypes/v1/
├── README.md                            (this file)
├── 01-custom_agents_md.md
├── 02-custom_agent.md
├── 03-subagent.md
├── 04-parallel_subagents.md
├── 05-skills.md
├── 06-plan_mode.md
├── 07-simple_tool_use.md
├── 08-sequential_tool_use.md
├── 09-parallel_tool_use.md
├── 10-tool_restriction_prompt.md
├── 11-tool_restriction_permissions.md
├── 12-pr_review_judgment.md             (new — closes review_judgment eval gap)
├── 13-tool_restriction_rerouting.md     (new — closes tool-restriction rerouting gap)
├── 14-structured_artifact_output.md     (new — closes localization format gap)
└── 15-multi_skill_composition.md        (new — closes multi-skill Tier D/E gap)
```

The first eleven (01–11) are *existing* archetypes — they've been used to generate the current training corpus. The last four (12–15) are *new* archetypes proposed to close empirical evaluation gaps observed in v1 panel scoring.

## Empirical motivation for the four new archetypes

When trained models are scored against the v1 benchmark, three categories show very low pass-rates relative to the rest of the suite:

| benchmark category | observed strict (weaker models) | symptom |
|---|---|---|
| `review_judgment` | ≈ 0% | model produces structured findings instead of literal `YES`/`NO` + `<review>` block |
| `tool_restriction` | ≈ 20% | model respects allowed tools, fails to *reroute* when natural tool is denied |
| `code_localization` | ≈ 20–30% | model finds the right files, fails to emit the strictly-formatted `location.txt` artifact |

The four new archetypes target each gap directly:

- **12 — `pr_review_judgment`**: trains the literal `YES`/`NO` + `<review>...</review>` output schema.
- **13 — `tool_restriction_rerouting`**: trains creative tool-substitution under denial (write→bash echo, grep→bash rg, read→subagent dispatch, etc.).
- **14 — `structured_artifact_output`**: trains strict per-line file artifacts (file-path + dotted qualified name, lex-sorted, anchored).
- **15 — `multi_skill_composition`**: trains 2–3-skill composition (sequential, DAG, prose-chain, selectivity-with-distractors).

The fourth gap (skill Tier D/E) was already partly covered by archetype 05 but in single-skill form; archetype 15 extends it to compositions.

## Overlap discipline

**Every example in this folder uses synthetic projects, made-up function names, and made-up skill names.** No example reuses any function name, file path, or skill name that appears in `data/samples_v1.jsonl` (the benchmark manifest). This is enforced by a denylist check; see the bottom of each file for the cross-reference notes.

If you add a new example, make sure it does not:

- name a function the benchmark edits or locates (`iter_slices`, `unquote_header_value`, `dispatch_hook`, `address_in_network`, `urldefragauth`, `make_default_short_help`, `_split_opt`, etc. — full list in the verifier);
- use a benchmark skill name (`review-flow`, `audit-flow`, `summary-flow`, `validate-train`, `count-imports`, `compute-checksum`, `naming-convention`, `api-style`, `encoding-convention`, etc.);
- mirror a benchmark prompt scenario (PR-review of `iter_slices`, multi-file caller-fanin into `RequestsCookieJar.update`, etc.).

## Output schema convention

Every archetype's "Output fields" block defines a JSON object the generator emits per sample. The fields are intentionally minimal and consumable by the downstream training-data pipeline. Where an archetype needs a multi-file fixture, it returns it through `pre_command` (a bash script) rather than embedding files directly — this matches the convention used by the benchmark's own per-sample `pre_command` field.
