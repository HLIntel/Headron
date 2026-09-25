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
