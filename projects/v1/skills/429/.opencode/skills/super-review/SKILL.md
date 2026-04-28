---
name: super-review
description: Comprehensive code review skill that handles the full review workflow itself. Use when the user asks for a full code review and points to this skill specifically.
---

When asked to perform a comprehensive review:

1. Read the target file.
2. Count TODO comments.
3. Write `review.md` at the repo root with this exact format:

   ```
   # Review: <basename of the target file>
   ## TODO Count: <integer count>
   ## Issues
   <one short bullet per TODO, or the literal text "No outstanding TODOs found." if zero>
   ```

The review must include the `# Review:` heading and the `## TODO Count:`
subheading exactly as shown. This skill is self-contained and does not
require invoking other skills.
