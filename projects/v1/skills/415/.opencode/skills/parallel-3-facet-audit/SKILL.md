---
name: parallel-3-facet-audit
description: Three-facet audit workflow for the autoresearch repo. Use when the user asks to audit this repo and produce a structured report.
---

When asked to audit this `autoresearch` repo, follow these steps:

1. **In a single assistant turn**, dispatch THREE `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: read `train.py` and report the four optimizer-related
     module-level constants `EMBEDDING_LR`, `UNEMBEDDING_LR`, `MATRIX_LR`,
     `WEIGHT_DECAY` with their values.
   - Subagent 2: read `train.py` and list the names of all top-level
     classes (e.g. `class GPTConfig`, `class GPT`), in source-file order.
   - Subagent 3: read `prepare.py` and report the tokenizer constants
     `MAX_SEQ_LEN`, `VOCAB_SIZE`, `BOS_TOKEN` with their values.

2. After all three subagents return, write `report.md` at the repo root
   with three sections:

   ```
   # Audit

   ## Optimizer
   EMBEDDING_LR: <v>
   UNEMBEDDING_LR: <v>
   MATRIX_LR: <v>
   WEIGHT_DECAY: <v>

   ## Classes
   <one class name per line>

   ## Tokenizer
   VOCAB_SIZE: <v>
   ```

Do NOT call `read`, `grep`, `glob`, or `bash` directly from the parent;
only the subagents inspect files. The parent agent is responsible for
the final `write`.
