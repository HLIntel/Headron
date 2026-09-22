# Anti-Mutation Engineering

Mutation is not inherently bad. Uncontrolled mutation is.

## State classes
### Immutable
Use for configuration, identifiers, contracts, snapshots, messages, historical records, and shared cache values.

### Owned mutable
Use for local algorithmic work, buffers, builders, and temporary state. Make ownership explicit.

### Transactional
Use for persistent state, critical updates, financial or accounting state, configuration changes, and high-impact agent operations.

## Five-layer model
PREVENT -> DETECT -> ISOLATE -> VERSION -> RECOVER

### Prevent
Rust ownership, frozen Python models, immutable mappings, TypeScript readonly APIs, and persistent data structures.

### Detect
Type checkers, static analysis, race detection, tests, property-based tests, fuzzing, and invariant checks.

### Isolate
Process boundaries, capability systems, sandboxing, path fencing, separate workspaces, and read-only mounts.

### Version
Revisions, content hashes, Git commits, snapshots, and append-only records.

### Recover
Transactions, WAL, backups, snapshots, rollback, and replay.

## Cache mutation problem
A cache hit that returns a mutable shared object can let the caller silently modify the cached value.

Possible solutions:
- immutable values
- defensive copying
- serialization boundaries
- copy-on-write
- explicit ownership transfer

## AI-specific mutation
AI agents create additional mutation surfaces across source code, configuration, CI, credentials, memory, tool definitions, and generated files.

High-impact mutations should have policy checks, snapshots, diffs, audit logs, approval gates, and rollback.