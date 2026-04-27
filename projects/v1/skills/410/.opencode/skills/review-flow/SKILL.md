---
name: review-flow
description: Code review workflow for this repository. Use when the user asks to review a code file for outstanding TODOs and produce a review document.
---

When asked to review a code file in this project, follow these steps in order:

1. Read the target file using the `read` tool.
2. Count the TODO comments (lines containing the literal `TODO`) in the file.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

The `# Review:` heading and `## TODO Count:` subheading are required substrings.
