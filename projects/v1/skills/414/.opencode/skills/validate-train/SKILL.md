---
name: validate-train
description: Run the bundled training-pipeline validation script and report its output token. Use when the user asks to validate the autoresearch training pipeline.
---

Run `scripts/validate.py` (relative to the skill base directory) and report the
captured `VALID_<hex>` token. This skill is specific to training-pipeline
validation; it does NOT cover general file analysis or summarization.
