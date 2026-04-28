---
name: code-coverage-report
description: Generate a code-coverage report from the project's test suite. Use ONLY when the user asks for test-coverage statistics.
---

To generate a coverage report, invoke `pytest --cov` via bash and write the
result to `coverage_report.md`. This skill produces test-coverage statistics;
it does NOT review code for issues, TODOs, or structural problems.
