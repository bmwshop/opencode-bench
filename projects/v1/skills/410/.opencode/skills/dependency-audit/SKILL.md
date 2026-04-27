---
name: dependency-audit
description: Third-party dependency audit workflow. Use when the user asks to audit which third-party packages this project depends on and what versions are pinned.
---

When asked to audit third-party dependencies:

1. Read the project's dependency file (`setup.py`, `pyproject.toml`, or
   `requirements.txt`) to enumerate declared third-party packages.
2. For each dependency, record its declared version constraint.
3. Write `dependencies.md` at the repo root with this format:

   ```
   # Dependencies
   - <package>: <version-constraint>
   ...
   ```

This skill is for DEPENDENCY audits, not code reviews. If the user is asking
to review CODE for TODOs or issues, this is the wrong skill -- the project
ships a `review-flow` skill for that.
