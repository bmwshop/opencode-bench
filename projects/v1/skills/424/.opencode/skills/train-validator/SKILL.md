---
name: train-validator
description: Validate the training pipeline (autoresearch). Runs the bundled training-validation script and reports the validation token. Use ONLY for training-pipeline validation.
---

To validate the training pipeline, run `scripts/validate.py` and report the
captured `VALID_<hex>` token. This skill is specific to training-pipeline
validation; it does NOT cover general file analysis or summarization.
