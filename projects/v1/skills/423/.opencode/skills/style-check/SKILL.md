---
name: style-check
description: Style-only review focused on formatting, naming, and PEP-8 conformance. Use when the user explicitly asks about formatting or style conventions; do NOT use for TODO-focused or generic code reviews.
---

For a style-only review:

1. Read the target file.
2. Identify PEP-8 / formatting issues (line length, naming, whitespace).
3. Write `style_review.md` at the repo root listing the formatting issues found.

This skill does NOT analyze logic or count TODOs. For TODO-focused reviews use
`todo-review`; for generic non-style reviews use `code-review`.
