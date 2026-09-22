# High-Assurance Builder Workflow

This is the default engineering workflow for serious AI-assisted development.

## Phase 1: Define
Write the goal, inputs, outputs, invariants, non-goals, resource budgets, security boundaries, and failure behavior.

## Phase 2: Constrain
Define types, schemas, timeouts, limits, permissions, allowed paths, allowed tools, and network boundaries.

## Phase 3: Implement
Prefer small interfaces, explicit state, pure functions where practical, immutable boundaries, bounded concurrency, deterministic serialization, and structured errors.

## Phase 4: Verify
Run format, lint, type checks, unit tests, integration tests, property tests, fuzzing, race and concurrency tests, security scans, and dependency audits.

## Phase 5: Inspect AI changes
Inspect the diff, changed dependencies, permissions, filesystem behavior, network behavior, tests, invariants, resource bounds, and rollback path.

## Phase 6: Release
Prefer reproducible builds, lockfiles, pinned actions or dependencies where appropriate, signed artifacts where appropriate, provenance, versioned schemas, changelogs, and rollback instructions.

## Questions before shipping
- What invalid inputs exist?
- What happens during partial failure?
- What happens when a dependency is slow or unavailable?
- What grows, and what is the maximum?
- Who owns each mutable object?
- What can the agent read, write, execute, and change?
- Which actions require approval?
- Can high-impact state be reconstructed or rolled back?