---
name: chain-read-grep-edit
description: Three-step chain for finding all occurrences of a literal string in a small repo. Use when the user asks to enumerate all occurrences of a pattern.
---

When asked to find every occurrence of a literal string:

1. **Read** the canonical target file using the `read` tool. (For an
   audit of `WEIGHT_DECAY` in autoresearch, the file is `train.py`.)
2. **Grep** for the literal string using the `grep` tool, scoped to the
   repo root.
3. **Write** an `occurrences.md` artifact at the repo root, containing
   one line per match in the format `<filepath>:<line_number>` (sorted
   by line number ascending).

Issue exactly ONE call of each tool, in this exact order: `read`, then
`grep`, then `write`. No other tools.
