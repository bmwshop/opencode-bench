# #16 knowledge

## Category

skill

## Project

skill_knowledge

## Capability

Knowledge-based skill invocation. Opencode supports skills -- reusable instruction bundles defined as `SKILL.md` files with YAML frontmatter. Skill names and descriptions are injected into the system prompt, and the model uses the `skill` tool to load the full content on demand. This test verifies the model recognizes when a skill is relevant, loads it, and follows its conventions when generating code.

## Setup

The project configures skills via `opencode.json`: `"skills": { "paths": [".opencode/skills"] }`. A skill named `api-style` is defined at `.opencode/skills/api-style/SKILL.md` with rules:
1. All API handler functions must be prefixed with `handle` (e.g., `handleRegister`)
2. Include the marker comment `// API_HANDLER` above each function
3. Return objects with shape `{ ok: boolean, data: any }`

The fixture includes `src/register.ts` with a non-conforming stub (`register` instead of `handleRegister`, no `API_HANDLER` marker). The model must load the skill, read the existing file, and rewrite it to conform to the skill's conventions.

## Prompt

> Create an API handler for user registration in src/register.ts

## Pass criteria (6 checks)

1. `any_tool_name` equals `skill` -- model invokes the skill tool
2. `any_tool_param_value` `skill.name` equals `api-style` -- loads the correct skill
3. `file_regex` `register.ts` matches `handle[A-Z]` -- function has the required handle prefix
4. `file_regex` `register.ts` matches `API_HANDLER` -- marker comment is present
5. `file_regex` `register.ts` matches `ok.*boolean` -- return type follows `{ ok: boolean, data: any }` shape
6. `tool_before` read → edit -- read before edit (filetime.assert enforced)

## Shortest path

**3 tool calls**: `skill` (with `name: "api-style"`) → `read src/register.ts` → `edit` to rewrite the stub with a conforming handler. The file exists, so `filetime.assert` requires a read before edit. No `max_tool_count` check constrains the upper bound.

## Fail modes

- Doesn't invoke the `skill` tool -- writes code without consulting the project's style conventions
- Loads the skill but ignores its rules (no `handle` prefix, missing marker comment, or wrong return shape)
- Uses a different skill name
- Skips reading the file before editing (blocked by `filetime.assert`)
