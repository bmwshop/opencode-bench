---
name: code-review
description: Code-quality review focused on outstanding issues, TODOs, and structural concerns. Use when the user asks for a code review.
---

When asked to review a code file:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this format:
   ```
   # Review: <basename>
   ## TODO Count: <integer>
   ## Issues
   <one bullet per TODO, or "No outstanding TODOs found.">
   ```

This is the code-quality review skill. NOT for code formatting (use
`code-style-format`). NOT for test coverage (use `code-coverage-report`).
