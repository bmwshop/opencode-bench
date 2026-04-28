---
name: dag-two-inputs-one-output
description: Two-parallel-input, one-output workflow that fetches values from two files and combines them. Use when producing a small "combined values" artifact from two source files.
---

When asked to produce a combined-values artifact from two source files:

1. **In a single assistant turn**, dispatch TWO `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: read the first source file and return the requested
     value (e.g. `EMBEDDING_LR` from `train.py`).
   - Subagent 2: read the second source file and return the requested
     value (e.g. `VOCAB_SIZE` from `prepare.py`).

2. After both return, write the output file (e.g. `combined.py`) at the
   repo root containing exactly two assignment lines (and no others):

   ```
   <FIRST_NAME> = <value from subagent 1>
   <SECOND_NAME> = <value from subagent 2>
   ```

Do NOT call `read`, `grep`, `glob`, or `bash` directly from the parent;
only the subagents inspect files.
