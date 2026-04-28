---
name: comment-review
description: Review of all kinds of comments in a code file (TODOs, FIXMEs, XXXs, license headers, docstrings). Use when the user asks for a comprehensive comment audit, NOT a TODO-only review.
---

For a comprehensive comment audit:

1. Read the target file.
2. Categorize all comments by type (TODO, FIXME, XXX, license, docstring, inline).
3. Write `comments.md` at the repo root.

This skill is NOT focused on TODOs only. For TODO-only reviews, use the
`todo-review` skill instead.
