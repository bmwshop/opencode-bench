# #1 camel_case

## Category

agents_md

## Project

camel_case

## Capability

AGENTS.md instruction following. Opencode automatically injects the contents of a project's `AGENTS.md` file into the model's system prompt. This test verifies the model reads and obeys project-specific style conventions defined in AGENTS.md, even when they contradict language defaults (Python's PEP 8 snake_case convention).

## Setup

The project's `AGENTS.md` contains a single style rule: "Use camelCase for all function and variable names, even in Python." The fixture already includes `src/convert.py` with a correct camelCase implementation (`fahrenheitToCelsius`). The model is expected to write or overwrite this file following the convention.

## Prompt

> Write a function that converts Fahrenheit to Celsius. Write it to src/convert.py

## Pass criteria (2 checks)

1. `file_regex` `src/convert.py` matches `def\s+[a-z]+[A-Z]\w*\(` -- function name is camelCase
2. `file_regex` `src/convert.py` does NOT match `def\s+[a-z]+_[a-z]` -- no snake_case function names

## Shortest path

The fixture already has `src/convert.py` with correct camelCase content. Both `write` and `edit` enforce `filetime.assert` on existing files, so the minimum clean path is **2 tool calls** (read + write/edit). No `max_tool_count` check constrains the upper bound.

**Caveat**: A model that reads the file and stops also passes (1 tool call), since the file already satisfies both checks.

## Fail modes

- Uses Python's default snake_case convention (`fahrenheit_to_celsius`) -- indicates the model ignored AGENTS.md
- Uses camelCase but also includes snake_case helper functions
- Doesn't create the file at all
