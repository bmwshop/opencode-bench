# v1 #39 locate_prepare_cookies_tokens

## Category

code_localization

## Contract

completion

## Surface

tools

## Repo

`requests` — psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Difficulty tier

**medium**. See `data/v1_localization_criteria.json` for the full tier-diversity matrix covering all 10 v3c structured samples.

## Structural signature

```
{
  "template": "T1",
  "scope_kind": "three_files",
  "anchor_kind": "instance_method",
  "answer_entries": 4,
  "answer_files": 3,
  "unique_trait": "prepared_request_cookies_reprep_fanin_from_auth_and_redirect"
}
```

No other v3c sample in this tier shares this exact signature. See the `convert_22-30_v3c_tiered` plan for the diversity argument.

## Design

Template **T1** (anchor + direct callers). The agent must identify

1. the anchor function (semantic description), and
2. every function under the given scope whose body contains a direct call resolving by name to the anchor.

Anchor: `src/requests/models.py::prepare_cookies` (`method`).

Scope: `['src/requests/auth.py', 'src/requests/models.py', 'src/requests/sessions.py']`.

Answer shape: 4 entries across 3 file(s). Unique structural trait: `prepared_request_cookies_reprep_fanin_from_auth_and_redirect`.

## Ground truth (gold answer)

Derived mechanically by [scripts/derive_039_ground_truth.py](../../../scripts/derive_039_ground_truth.py) against pin `79f4df84cf77`. 4 entries, already in lexicographic order:

```text
src/requests/auth.py::HTTPDigestAuth.handle_401
src/requests/models.py::PreparedRequest.prepare
src/requests/models.py::PreparedRequest.prepare_cookies
src/requests/sessions.py::SessionRedirectMixin.resolve_redirects
```

SHA-256 of the gold string (with trailing newline): `b7268d6e04fc8236886a561ee66a07d2eddc47170da565f1da7c7d5a7d897822`.

## Five-layer verification

1. **AST derivation** via the shared [scripts/localization_oracle.py](../../../scripts/localization_oracle.py) (`T1` template). Every `FunctionDef` / `AsyncFunctionDef` in scope is walked; `ast.Call` nodes whose `func.id` or `func.attr` matches the anchor/target name produce the "direct call" relation.
2. **`rg` cross-check**: every AST-discovered call line must appear in `rg -n -w --with-filename <name> <scope_files>` output. Catches dynamic/meta-programming patterns or AST/rg drift.
3. **Anchor-kind assertion**: the oracle asserts exactly one `prepare_cookies` definition matching the declared `module_level=False` kind in `src/requests/models.py`, with no decorators, before emitting gold.
4. **Evaluator audit** via [scripts/audit_localization_structured.py](../../../scripts/audit_localization_structured.py): Pass 1 (positive + negative `location.txt` variants through the real `file_regex_disk` evaluator) and Pass 2 (end-to-end `eval.evaluate()` with synthesized trace).
5. **Pilot panel** (post-locking): 5 models × 3 seeds; top-tier model must reach ≥ 2/3; per-tier pass-rate correlation matrix < 0.85 between any two samples in the same tier.

## Setup

The per-run fixture is a pinned copy of `psf/requests`. The agent writes a single deliverable — `location.txt` — at the root of the per-run workspace. No other files may be modified (enforced indirectly by `call_schema_valid` catching malformed `write`/`edit` args).

## Prompt

> In this `requests` checkout, a `PreparedRequest` builds the outgoing `Cookie` header from a merged cookie jar; the same method is re-invoked from auth flows (digest challenge retry) and from the session's redirect-following loop to refresh the header after the request target changes.
>
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function matching either:
>
> - the instance method on `PreparedRequest` in `src/requests/models.py` that builds the `Cookie` header for the outgoing request, or
> - every function defined in `src/requests/auth.py`, `src/requests/models.py`, or `src/requests/sessions.py` (any nesting depth, including methods on classes and mixins) whose body directly calls that method.
>
> Each line is `file_path::QualifiedName` — repo-relative path followed by `::` and the dotted qualified name of the function. Module-level functions use their bare name (e.g. `merge_cookies`); methods on classes or mixins use `ClassName.method` (e.g. `Session.prepare_request`); nested closures use `outer.inner` (e.g. a helper `generate` defined inside `Response.iter_content` is written `Response.iter_content.generate`). End with a single trailing newline.

## Pass criteria (2 checks)

1. `file_regex_disk` `location.txt` — anchored regex demanding the exact 4-line gold above, optional trailing newline. Any deviation (wrong function, wrong file, missing/added entry, wrong qualname style, wrong sort, extra content) fails.
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

