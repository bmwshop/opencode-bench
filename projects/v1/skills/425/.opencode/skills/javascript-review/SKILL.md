---
name: javascript-review
description: Code review workflow for JavaScript and TypeScript files. Use when the user asks to review a `.js`, `.ts`, `.tsx`, or `.jsx` file for outstanding TODOs.
---

When asked to review a JavaScript or TypeScript file:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this format:
   ```
   # Review: <basename>
   ## TODO Count: <integer>
   ## Issues
   <one bullet per TODO>
   ```

This skill is for JavaScript / TypeScript files only. For Python files,
use `python-review`.
