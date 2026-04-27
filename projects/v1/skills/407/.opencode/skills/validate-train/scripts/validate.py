#!/usr/bin/env python3
"""Trivial validation script for the validate-train skill (sample #407).

Prints a single-line validation token. The token is hard-coded at the pinned
commit so the audit harness can verify the model's response includes it. In a
real validation script this would inspect repo state and emit a derived token;
here we keep it deterministic for the bench.
"""
print("VALID_a8c9f1e2")
