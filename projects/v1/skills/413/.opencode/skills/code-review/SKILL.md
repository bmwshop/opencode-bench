---
name: code-review
description: Generic code review for any Python file. Use for general analysis covering structure, complexity, and idiomatic style. NOT focused on TODOs specifically -- if the user asks about TODOs, use `todo-review` instead.
---

For a generic code review:

1. Read the target file.
2. Identify structural concerns (long functions, unclear names, missing docstrings).
3. Write `code_review.md` at the repo root summarizing the findings as prose.

This skill produces a generic prose review. It does NOT itemize TODO comments;
for that, use the `todo-review` skill (which is specifically for TODO-focused
analysis and produces a structured `review.md` with explicit TODO counting).
