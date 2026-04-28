---
name: python-review
description: Code review workflow for Python files. Use when the user asks to review a `.py` file for outstanding TODOs.
---

When asked to review a Python file:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this format:
   ```
   # Review: <basename>
   ## TODO Count: <integer>
   ## Issues
   <one bullet per TODO, or "No outstanding TODOs found.">
   ```

This skill is for Python files only. For JavaScript / TypeScript files,
use `javascript-review`.
