# #13 camel_case

- **Category:** agents_md
- **Project:** camel_case

## Capability

AGENTS.md instruction following. Opencode automatically injects the contents of a project's `AGENTS.md` file into the model's system prompt. This test verifies the model reads and obeys project-specific style conventions defined in AGENTS.md, even when they contradict language defaults (Python's PEP 8 snake_case convention).

## Setup

The project's `AGENTS.md` contains a single style rule: "Use camelCase for all function and variable names, even in Python." There are no other source files -- the model must create a new file from scratch following this convention.

## Prompt

> Write a function that converts Fahrenheit to Celsius. Write it to src/convert.py

## Pass criteria

- The written file contains a function with a camelCase name (e.g., `fahrenheitToCelsius`, `convertTemp`)
- No snake_case function names appear (e.g., `fahrenheit_to_celsius`)

## Fail modes

- Uses Python's default snake_case convention (`fahrenheit_to_celsius`) -- indicates the model ignored AGENTS.md
- Uses camelCase but also includes snake_case helper functions
- Doesn't create the file at all
