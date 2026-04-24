# v1 #49 locate_digest_header_tokens

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
  "scope_kind": "single_file",
  "anchor_kind": "instance_method",
  "answer_entries": 3,
  "answer_files": 1,
  "unique_trait": "digest_header_builder_with_nested_sha_helper_and_challenge_retry"
}
```

No other v3c sample in this tier shares this exact signature. See the `convert_22-30_v3c_tiered` plan for the diversity argument.

## Design

Template **T1** (anchor + direct callers). The agent must identify

1. the anchor function (semantic description), and
2. every function under the given scope whose body contains a direct call resolving by name to the anchor.

Anchor: `src/requests/auth.py::build_digest_header` (`method`).

Scope: `['src/requests/auth.py']`.

Answer shape: 3 entries across 1 file(s). Unique structural trait: `digest_header_builder_with_nested_sha_helper_and_challenge_retry`.

## Ground truth (gold answer)

Derived mechanically by [scripts/derive_049_ground_truth.py](../../../scripts/derive_049_ground_truth.py) against pin `79f4df84cf77`. 3 entries, already in lexicographic order:

```text
src/requests/auth.py::HTTPDigestAuth.__call__
src/requests/auth.py::HTTPDigestAuth.build_digest_header
src/requests/auth.py::HTTPDigestAuth.handle_401
```

SHA-256 of the gold string (with trailing newline): `d763a3f6f11299cb87cf67db58b5e28074f1d4f53fff83845b5c63e00a1dc0d3`.

## Five-layer verification

1. **AST derivation** via the shared [scripts/localization_oracle.py](../../../scripts/localization_oracle.py) (`T1` template). Every `FunctionDef` / `AsyncFunctionDef` in scope is walked; `ast.Call` nodes whose `func.id` or `func.attr` matches the anchor/target name produce the "direct call" relation.
2. **`rg` cross-check**: every AST-discovered call line must appear in `rg -n -w --with-filename <name> <scope_files>` output. Catches dynamic/meta-programming patterns or AST/rg drift.
3. **Anchor-kind assertion**: the oracle asserts exactly one `build_digest_header` definition matching the declared `module_level=False` kind in `src/requests/auth.py`, with no decorators, before emitting gold.
4. **Evaluator audit** via [scripts/audit_localization_structured.py](../../../scripts/audit_localization_structured.py): Pass 1 (positive + negative `location.txt` variants through the real `file_regex_disk` evaluator) and Pass 2 (end-to-end `eval.evaluate()` with synthesized trace).
5. **Pilot panel** (post-locking): 5 models × 3 seeds; top-tier model must reach ≥ 2/3; per-tier pass-rate correlation matrix < 0.85 between any two samples in the same tier.

## Setup

The per-run fixture is a pinned copy of `psf/requests`. The agent writes a single deliverable — `location.txt` — at the root of the per-run workspace. No other files may be modified (enforced indirectly by `call_schema_valid` catching malformed `write`/`edit` args).

## Prompt

> In this `requests` checkout, an `HTTPDigestAuth` method builds the full `Authorization: Digest ...` header value for a given request and a previously parsed `WWW-Authenticate` challenge; the class's `__call__` entry-point relies on it on the first attempt, and its `handle_401` 401-retry path re-invokes it after parsing the challenge. The method also defines a small nested `sha_utf8` helper that is *not* itself a caller.
>
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
>
> - the `HTTPDigestAuth` instance method in `src/requests/auth.py` that builds the `Digest` auth header value, or
> - every function defined in `src/requests/auth.py` (any nesting depth, including methods on classes, mixins, and nested closures) whose body directly calls that method.
>
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (2 checks)

1. `file_regex_disk` `location.txt` — anchored regex demanding the exact 3-line gold above, optional trailing newline. Any deviation (wrong function, wrong file, missing/added entry, wrong qualname style, wrong sort, extra content) fails.
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

