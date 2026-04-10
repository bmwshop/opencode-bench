---
name: review-flow
description: Code review workflow. Use when asked to review code files.
---
When reviewing code, follow these steps in order:
1. Read the target file
2. Run: grep -c "TODO" <file> to count TODOs
3. Write findings to review.md with this exact format:
   # Review: <filename>
   ## TODO Count: <n>
   ## Issues
   <your findings>
