# Verification Loops

Use the smallest loop that catches the class of failure being changed, then run the full applicable loop before completion.

## Python
```bash
ruff check .
ruff format --check .
pyright
pytest
```

Add Hypothesis/property tests for parsers, state machines, financial/data transforms, validators, and edge-heavy logic.

## Rust
```bash
cargo fmt --check
cargo check --workspace
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
cargo audit
cargo deny check
```

Use Miri and loom for targeted advanced verification.

## Go
```bash
gofmt -l .
go vet ./...
go test ./...
go test -race ./...
staticcheck ./...
govulncheck ./...
```

Use Go fuzzing for parsers and boundary logic.

## TypeScript
```bash
npx tsc --noEmit
npx eslint .
npm test
```

Use Ajv/Valibot checks at external boundaries.

## Cross-language
```text
format
-> lint
-> type check
-> unit tests
-> integration tests
-> property/fuzz tests
-> security scans
-> dependency audit
-> build
-> diff review
```

## AI change verification
Do not let the agent declare success from a passing unit test alone when the change affects:
- permissions
- shell commands
- filesystem boundaries
- network access
- schemas
- concurrency
- caches
- dependency manifests
- CI workflows
- deployment configuration

Those changes need the relevant policy/security checks and a human-reviewable diff.