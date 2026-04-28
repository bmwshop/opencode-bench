---
name: validate-train
description: Project validation workflow for autoresearch training scripts. Use when asked to validate the training pipeline.
---

To validate the training pipeline:

1. Run the bundled validation script: `scripts/validate.py` (relative to the
   skill base directory).
2. Capture its output token (a `VALID_<hex>` line).
3. Report the captured token to the user.

This skill is for `autoresearch` training-script validation. It does NOT apply
to general code review.
