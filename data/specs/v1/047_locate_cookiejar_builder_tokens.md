# v1 #47 locate_cookiejar_builder_tokens

## Category

code_localization

## Contract

completion

## Surface

tools

## Repo

`requests` — psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Difficulty tier

**hard**. See `data/v1_localization_criteria.json` for the full tier-diversity matrix covering all 10 v3c structured samples.

## Structural signature

```
{
  "template": "T1",
  "scope_kind": "four_files",
  "anchor_kind": "module_level",
  "answer_entries": 7,
  "answer_files": 4,
  "unique_trait": "module_level_builder_plus_model_and_session_lifecycle_fanin"
}
```

No other v3c sample in this tier shares this exact signature. See the `convert_22-30_v3c_tiered` plan for the diversity argument.

## Design

Template **T1** (anchor + direct callers). The agent must identify

1. the anchor function (semantic description), and
2. every function under the given scope whose body contains a direct call resolving by name to the anchor.

Anchor: `src/requests/cookies.py::cookiejar_from_dict` (`module-level`).

Scope: `['src/requests/cookies.py', 'src/requests/models.py', 'src/requests/sessions.py', 'src/requests/utils.py']`.

Answer shape: 7 entries across 4 file(s). Unique structural trait: `module_level_builder_plus_model_and_session_lifecycle_fanin`.

## Ground truth (gold answer)

Derived mechanically by [data/scripts/derive_047_ground_truth.py](../../scripts/derive_047_ground_truth.py) against pin `79f4df84cf77`. 7 entries, already in lexicographic order:

```text
src/requests/cookies.py::cookiejar_from_dict
src/requests/cookies.py::merge_cookies
src/requests/models.py::PreparedRequest.prepare_cookies
src/requests/models.py::Response.__init__
src/requests/sessions.py::Session.__init__
src/requests/sessions.py::Session.prepare_request
src/requests/utils.py::add_dict_to_cookiejar
```

SHA-256 of the gold string (with trailing newline): `d99aad774d5fbd30e153691a325b1b5c67b2608ccfa630e67737ca6f87669ca4`.

## Five-layer verification

1. **AST derivation** via the shared [data/scripts/localization_oracle.py](../../scripts/localization_oracle.py) (`T1` template). Every `FunctionDef` / `AsyncFunctionDef` in scope is walked; `ast.Call` nodes whose `func.id` or `func.attr` matches the anchor/target name produce the "direct call" relation.
2. **`rg` cross-check**: every AST-discovered call line must appear in `rg -n -w --with-filename <name> <scope_files>` output. Catches dynamic/meta-programming patterns or AST/rg drift.
3. **Anchor-kind assertion**: the oracle asserts exactly one `cookiejar_from_dict` definition matching the declared `module_level=True` kind in `src/requests/cookies.py`, with no decorators, before emitting gold.
4. **Evaluator audit** via [data/scripts/audit_localization_structured.py](../../scripts/audit_localization_structured.py): Pass 1 (positive + negative `location.txt` variants through the real `file_regex_disk` evaluator) and Pass 2 (end-to-end `eval.evaluate()` with synthesized trace).
5. **Pilot panel** (post-locking): 5 models × 3 seeds; top-tier model must reach ≥ 2/3; per-tier pass-rate correlation matrix < 0.85 between any two samples in the same tier.

## Setup

The per-run fixture is a pinned copy of `psf/requests`. The agent writes a single deliverable — `location.txt` — at the root of the per-run workspace. No other files may be modified (enforced indirectly by `call_schema_valid` catching malformed `write`/`edit` args).

## Prompt

> In this `requests` checkout, a module-level helper in `src/requests/cookies.py` converts a plain dict (or `None`) into a `RequestsCookieJar`; it is the single construction path used to materialize session-level, request-level, and response-level cookie containers across the library, and a sibling cookie-merge helper and a utility API alias delegate to it directly.
>
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
>
> - the module-level helper in `src/requests/cookies.py` that constructs a `RequestsCookieJar` from a dict, or
> - every function defined in `src/requests/cookies.py`, `src/requests/models.py`, `src/requests/sessions.py`, or `src/requests/utils.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that helper.
>
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (2 checks)

1. `file_regex_disk` `location.txt` — anchored regex demanding the exact 7-line gold above, optional trailing newline. Any deviation (wrong function, wrong file, missing/added entry, wrong qualname style, wrong sort, extra content) fails.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**≥ 2 tool calls** in practice: at least one `grep`/`bash rg` (or equivalent) to locate the relevant functions with enough context to resolve enclosing class + nesting, plus one `write` of `location.txt`. Careful agents add `read` calls to confirm function boundaries but are not required to by the rubric.

## Known fail modes

- Wrong/missing entry (e.g. overlooks a mixin caller, picks the wrong anchor) — anchored regex fails.
- Class prefix dropped (e.g. `send` instead of `Session.send`) or added on a module-level function — regex fails.
- Nested closure missed (e.g. `Response.iter_content.generate` flattened to `generate` or to `iter_content.generate` without the outer class) — regex fails.
- Paths written without the `src/requests/` prefix, or with a leading `./` — regex fails.
- Entries out of lexicographic order — regex fails.
- Malformed `write` args (e.g. `path` instead of `filePath`) — `call_schema_valid` fails even if the content would have matched.

## Intentionally *not* checked

- Free-form explanation text — only `location.txt` is scored.
- Which tools the agent uses to explore (`read`, `grep`, `glob`, `bash rg`, etc.) — any mix that produces the exact gold passes.
- Whether the agent reasons about inheritance, lifecycle, or mixin resolution order — only the artifact matters.

## Note on methodology

This sample is part of the v3c family — a natural-language, structured-output localization task. It is a deliberate divergence from both `arXiv:2604.05013` (semantic file-level localization, too ambiguous) and the pre-v3c criterion-anchored design (mechanical but too easy — trivially solved by a single `rg -l -w`). The natural-language prompt stresses reading comprehension; the dotted-qualname discipline forces a search → read → write pipeline that still exercises opencode's tool-use surface (the agent must resolve which function each call site belongs to, which a single-shot `rg` cannot answer). Ground-truth determinism is preserved by the five-layer verification protocol above.

If the submodule pin changes, re-run the deriver and update the gold, the regex, and the SHA-256 here.

