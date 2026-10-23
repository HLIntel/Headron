# JSON, Schemas, and Data Contracts

JSON should be treated as an external data boundary.

## Core technologies
- JSON Schema
- Ajv
- Pydantic JSON Schema
- msgspec
- JSON Type Definition

## Boundary pipeline
bytes -> size limits -> parser -> schema validation -> normalization -> typed model -> application

## Resource bounds
Use constraints for maxLength, maxItems, maxProperties, minimum, maximum, required properties, additionalProperties, pattern, and format.

Also study parser-level limits where available.

## Security topics
- duplicate-key ambiguity
- prototype pollution
- deeply nested input
- giant arrays
- giant strings
- giant numbers
- parser differentials
- schema confusion
- unsafe deserialization
- resource exhaustion
- canonicalization
- versioned contracts

## Cross-language contracts
JSON Schema can become the stable interface across Python, Rust, Go, and TypeScript implementations.

## Thea convention: contracts and receipts
- A **contract** is a declared JSON shape under `tools/*.schema.json`, checked by the one validator, `scripts/packmanifest.py`. A `--json` record is named by one of these schemas.
- A **receipt** is the part of a run record that binds a verdict to what it was measured over: `contract` (the sha256 of the canonical contract), `base`, and `head`. Build it only with `agentpolicy.receipt()`, and check it with `agentpolicy.receipt_errors()` against `$defs/outcome/properties/receipt` in `tools/agent-task.schema.json`.
- A receipt that does not match its schema is refused, not reported as a warning: an unbound verdict is not a verdict.
- The receipt cases live in `scripts/agent_test.py` (`receipt_cases`).
