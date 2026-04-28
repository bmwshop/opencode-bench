---
name: dependency-audit
description: Third-party dependency audit workflow. Use when the user asks to audit which third-party packages this project depends on and what versions are pinned.
---

When asked to audit third-party dependencies:

1. Read the project's dependency file (`setup.py`, `pyproject.toml`, or
   `requirements.txt`) to enumerate declared third-party packages.
2. Record each dependency's declared version constraint.
3. Write `dependencies.md` at the repo root with one bullet per package.

This skill is for DEPENDENCY audits, not code reviews. If the user is asking to
review CODE for TODOs, use `review-flow` instead.
