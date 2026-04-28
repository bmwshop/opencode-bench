---
name: todo-review
description: Code review focused specifically on outstanding TODO comments. Use when the user asks about TODOs, technical debt markers, or wants a review that itemizes deferred work.
---

When asked to review a file's outstanding TODO comments:

1. Read the target file using the `read` tool.
2. Count lines containing the literal `TODO` (case-sensitive).
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

This is the TODO-specific review workflow. For style-only reviews, use
`style-check`. For generic code-quality reviews not focused on TODOs, use
`code-review`.
