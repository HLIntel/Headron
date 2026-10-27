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

## Data format evaluation and harvest (beyond raw YAML)

YAML carries notorious edge cases for autonomous agents: the "Norway problem" (`NO` parsed as boolean false), unquoted strings breaking parsers, and silent whitespace/indentation drift. Headron evaluates and harvests four modern alternatives:

1. **JSON with Strict Schemas (JSON Schema / Zod / Pydantic):**
   - *Advantage:* Zero ambiguity, deterministic parsing without heuristic guessing, native alignment with LLM tool-calling and function APIs.
   - *Headron Harvest:* All tool outputs, verdicts, and receipts validate strictly against frozen `tools/*.schema.json` via `scripts/packmanifest.py`.

2. **TOML (Tom's Obvious, Minimal Language):**
   - *Advantage:* Flat, table-compartmentalized structure mapped to a collision-free hash table with unambiguous scalar types; immune to indentation errors during agent patching.
   - *Headron Harvest:* Adopted for repository project and harness declarations (`pyproject.toml`, Rust `Cargo.toml`).

3. **Protocol Buffers / FlatBuffers:**
   - *Advantage:* Strictly typed, compiled binary data contracts with guaranteed forward/backward compatibility and low parsing overhead.
   - *Headron Harvest:* Wire contract for streaming agent-to-agent IPC, telemetry receipts, and real-time execution in companion runtimes (Mind API / HeadronOS).

4. **Code-as-Data (TypeScript / Python / DSLs):**
   - *Advantage:* Strong typing, immediate compiler/linter validation (e.g. `ast.parse`, `ruff`, `tsc`) preventing runtime crashes when an agent modifies configuration.
   - *Headron Harvest:* The `.headron` policy language and AST validation gates (`astshape.py`, `agentpolicy.py`) treat configurations as syntax trees, catching errors before commit.

## Headron convention: contracts and receipts
- A **contract** is a declared JSON shape under `tools/*.schema.json`, checked by the one validator, `scripts/packmanifest.py`. A `--json` record is named by one of these schemas.
- A **receipt** is the part of a run record that binds a verdict to what it was measured over: `contract` (the sha256 of the canonical contract), `base`, and `head`. Build it only with `agentpolicy.receipt()`, and check it with `agentpolicy.receipt_errors()` against `$defs/outcome/properties/receipt` in `tools/agent-task.schema.json`.
- A receipt that does not match its schema is refused, not reported as a warning: an unbound verdict is not a verdict.
- The receipt cases live in `scripts/agent_test.py` (`receipt_cases`).
