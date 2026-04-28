---
name: lint-runner
description: Run a Python linter (flake8) and emit a list of style violations. Use ONLY when the user asks for lint output or a style violation report.
---

To run the linter, invoke `flake8` via bash on the target file and report
the resulting violations. This skill produces a violation list; it does
NOT summarize file purpose or describe what the file does.
