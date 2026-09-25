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

`PREVENT -> DETECT -> ISOLATE -> VERSION -> RECOVER`

### Prevent

Rust ownership, frozen Python models, immutable mappings, TypeScript readonly APIs, persistent data structures, transactional database writes, and capability-limited tools.

### Detect

Type checkers, static analysis, race detection, tests, property-based tests, fuzzing, mutation testing, invariant checks, CodeQL, and dependency/security analysis where supported.

### Isolate

Process boundaries, capability systems, sandboxing, path fencing, separate workspaces, read-only mounts, and one mutable writer per worktree.

### Version

Revisions, content hashes, Git commits, snapshots, append-only records, schema versions, and dependency lockfiles.

### Recover

Transactions, WAL, backups, snapshots, rollback, replay, and controlled redeploy.

## Mutation testing

Mutation testing deliberately changes program behavior to test whether the existing test suite catches the change. It is a **test-suite verifier**, not a production-state strategy.

Use it:
- after functional tests exist
- on changed or high-value modules
- with bounded worker/time budgets
- against a known baseline
- as a quality signal before making it a hard repository-wide gate

Representative ecosystems include:
- Python: mutmut
- Rust: cargo-mutants
- TypeScript/JavaScript: StrykerJS
- F#/.NET: Stryker.NET

For languages without a mature mutation ecosystem, prefer property testing, fuzzing, differential/golden tests, sanitizers, fault injection, or proof checking rather than forcing a weak mutation tool into the stack.

## Cache mutation

A cache hit returning a mutable shared object can let a caller silently change cached state.

Use immutable values, defensive copies, serialization boundaries, copy-on-write, or explicit ownership transfer.

## AI-specific mutation

AI agents create mutation surfaces across source code, configuration, CI, credentials, memory, tool definitions, generated files, database state, and external services.

High-impact mutations should have policy checks, snapshots, diffs, audit logs, approval gates, and rollback.

See [patterns/BOUNDARY-BREAKAGE.md](BOUNDARY-BREAKAGE.md).

## What enforces this now

`atlas.yaml/governance_tiers` states which rules may move and on what terms, because **hard bounds
alone have one predictable failure: the wall that cannot move gets worked around.**

- **hard** — refuses, no argument. Irreversible, or observable outside this repository.
- **bounded** — an envelope. Reasoning is free inside it; moving the wall must NAME what earned
  it, judged by proportionality and reversibility for an add, and zero loss for a cut.
- **dynamic** — free, because the output contract is checked rather than the path to it.

Every ratchet must be named by the bounded tier, asserted both ways: an untiered bound is one
every reader classifies generously about their own change.

For an agent specifically, the controls in `agent_policy` refuse rather than warn, and
`agent_failure_modes` records the mistakes actually committed here — all of which look like
success from outside.
