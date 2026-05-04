# v1 #50 locate_utils_get_cluster_tokens

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
  "template": "T2",
  "scope_kind": "any_file",
  "target_kind": "module_level_functions",
  "answer_entries": 7,
  "answer_files": 3,
  "unique_trait": "hard_tier_five_get_helpers_cross_file_fanin"
}
```

No other v3c sample in this tier shares this exact signature. See the `convert_22-30_v3c_tiered` plan for the diversity argument.

## Design

Template **T2** (callers of a set). The agent must identify every function anywhere under the given scope whose body contains a direct call resolving by name to any of the given target names. Two conventions applied by the oracle and stated explicitly in the prompt:

- **Nested-def attribution**: a call site inside a nested `def` counts toward the enclosing function too, and the nested def is itself a separate entry (so both `outer` and `outer.inner` can appear in one answer).
- **Exclusion by name**: a function whose own unqualified name equals any target name is excluded, regardless of enclosing class or module (so a target `close` excludes every function literally named `close`, even on unrelated classes).

Targets: ['get_auth_from_url', 'get_netrc_auth', 'get_encoding_from_headers', 'get_unicode_from_response', 'get_encodings_from_content'] (kind: `module_level_functions`).

Scope: `src/requests/`.

Answer shape: 7 entries across 3 file(s). Unique structural trait: `hard_tier_five_get_helpers_cross_file_fanin`.

## Ground truth (gold answer)

Derived mechanically by [data/scripts/derive_050_ground_truth.py](../../scripts/derive_050_ground_truth.py) against pin `79f4df84cf77`. 7 entries, already in lexicographic order:

```text
src/requests/adapters.py::HTTPAdapter.build_response
src/requests/adapters.py::HTTPAdapter.proxy_headers
src/requests/adapters.py::HTTPAdapter.proxy_manager_for
src/requests/models.py::PreparedRequest.prepare_auth
src/requests/sessions.py::Session.prepare_request
src/requests/sessions.py::SessionRedirectMixin.rebuild_auth
src/requests/sessions.py::SessionRedirectMixin.rebuild_proxies
```

SHA-256 of the gold string (with trailing newline): `2468b7f3d6862df377f4e1a23237069f905ee1cd9ee021ea11683746599af9fe`.

## Five-layer verification

1. **AST derivation** via the shared [data/scripts/localization_oracle.py](../../scripts/localization_oracle.py) (`T2` template). Every `FunctionDef` / `AsyncFunctionDef` in scope is walked; `ast.Call` nodes whose `func.id` or `func.attr` matches the anchor/target name produce the "direct call" relation.
2. **`rg` cross-check**: every AST-discovered call line must appear in `rg -n -w --with-filename <name> <scope_files>` output. Catches dynamic/meta-programming patterns or AST/rg drift.
3. **Per-target cross-check**: a separate `rg` pass is run for each target name in `['get_auth_from_url', 'get_netrc_auth', 'get_encoding_from_headers', 'get_unicode_from_response', 'get_encodings_from_content']`; every per-target AST call site must appear in its rg output.
4. **Evaluator audit** via [data/scripts/audit_localization_structured.py](../../scripts/audit_localization_structured.py): Pass 1 (positive + negative `location.txt` variants through the real `file_regex_disk` evaluator) and Pass 2 (end-to-end `eval.evaluate()` with synthesized trace).
5. **Pilot panel** (post-locking): 5 models × 3 seeds; top-tier model must reach ≥ 2/3; per-tier pass-rate correlation matrix < 0.85 between any two samples in the same tier.

## Setup

The per-run fixture is a pinned copy of `psf/requests`. The agent writes a single deliverable — `location.txt` — at the root of the per-run workspace. No other files may be modified (enforced indirectly by `call_schema_valid` catching malformed `write`/`edit` args).

## Prompt

> In this `requests` checkout, five module-level helpers in `src/requests/utils.py` cooperate to extract request/response metadata: `get_auth_from_url` (pulls `user:pass` out of a URL), `get_netrc_auth` (looks up credentials in the user's `~/.netrc`), `get_encoding_from_headers` (picks the body encoding from the `Content-Type` header), `get_unicode_from_response` (decodes the response body using that encoding), and `get_encodings_from_content` (guesses encodings from HTML/XML body markup).
>
> Write `location.txt` at the repo root listing, one per line in lexicographic order, every function defined anywhere under `src/requests/` (any nesting depth, including methods on classes, mixins, and nested closures) whose body contains a direct call resolving by name to any of those five helpers. Both bare-name calls (`X(...)`) and attribute calls (`self.X(...)`, `obj.X(...)`) count. Lines that only import or re-export those names do not count.
>
> **Nested defs.** A call site physically inside a nested `def` (closure, inner helper) counts toward the enclosing function too — the enclosing function lexically contains that call site. The nested function is *also* a separate entry in its own right. So if a helper `generate` defined inside `Response.iter_content` contains a matching call, both `Response.iter_content` and `Response.iter_content.generate` appear in the answer.
>
> **Exclusion by name.** Any function whose own unqualified name equals one of the target names is excluded from the answer, regardless of the class or module it is defined on. The target names for this sample are the unqualified names listed above (e.g. `close`, not `Session.close`); a function literally named `close` on *any* class is therefore never in the answer, even if its body contains a matching attribute call like `adapter.close()`.
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

