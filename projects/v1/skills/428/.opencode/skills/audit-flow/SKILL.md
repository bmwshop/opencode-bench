---
name: audit-flow
description: Optimizer-constants audit workflow. Use when the user asks to audit the optimizer or learning-rate constants in train.py and produce a report.
---

When asked to audit this project's optimizer constants, follow these steps in order:

1. Read `train.py` using the `read` tool.
2. Identify the four optimizer-related module-level constants:
   - `EMBEDDING_LR`
   - `UNEMBEDDING_LR`
   - `MATRIX_LR`
   - `WEIGHT_DECAY`
3. Identify the tokenizer constants:
   - `VOCAB_SIZE`
   - `MAX_SEQ_LEN`
4. Write `audit.md` at the repo root with this exact format:

   ```
   # Audit: train.py
   ## Optimizer
   EMBEDDING_LR: <v>
   UNEMBEDDING_LR: <v>
   MATRIX_LR: <v>
   WEIGHT_DECAY: <v>
   ## Tokenizer
   VOCAB_SIZE: <v>
   MAX_SEQ_LEN: <v>
   ```

The `# Audit:` heading and `## Optimizer` / `## Tokenizer` subheadings are required;
the hidden grader checks for them. Values must be transcribed from the actual file.
