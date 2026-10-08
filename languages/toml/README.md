# TOML

Status: production.

## Purpose
Tool and package configuration: pyproject, Cargo, wrangler, linter settings.

## State
Tables may not be redefined; dotted keys and table headers both create tables. Types are explicit.

## Verify
parse -> schema validation -> the tool that owns the file loads it.
