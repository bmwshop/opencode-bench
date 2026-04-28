---
name: code-style-format
description: Auto-format code per a style spec (black, prettier, etc.). Use ONLY when the user asks to reformat or apply a code style.
---

To apply code formatting, invoke the project's formatter via bash and report
diffs. This skill REWRITES files according to a style spec; it does NOT
audit for outstanding issues, TODOs, or structural problems.
