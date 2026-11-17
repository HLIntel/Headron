# Lean 4

**Status:** production-specialized/research

## Purpose
Formal verification, theorem proving, proof-producing programs, and machine-checked invariants.

## Stack
Lean -> Lake -> Mathlib where appropriate -> editor tooling -> theorem/proof checks.

## Core practice
Treat the specification as a first-class artifact. A proof validates the formal statement, so specification quality is part of engineering correctness.

## Common mistakes
- proving the wrong abstraction
- encoding implementation details instead of system invariants
- making proofs unreadable or brittle

## Streamline
Define reusable lemmas and domain abstractions. Keep computational code and proof obligations separated when that improves maintainability.

## AI directive
Use Lean as an independent verifier for high-value invariants. Never accept a natural-language claim that a proof exists until Lean checks it.

## Verify
Lean/Lake build plus theorem checks; CI should compile proofs just as it compiles code.

Official: https://lean-lang.org/

## Operating card

**Route:** formal verification, proof-producing software, theorem proving, correctness-critical algorithms.

**Fast path:** lake project → `lake build` → focused theorem checks → `lake test` where applicable.

**Native authority:** Lean compiler, kernel, Lake, mathlib when used.

**Pair with:** Python/Rust/Go for executable systems whose critical algorithms are specified or verified in Lean.

**Boundary:** treat theorem statements and executable interfaces as contracts; minimize trusted axioms.

**Avoid:** proving irrelevant properties, opaque automation without understanding, oversized theorem dependencies.

**Reliability:** proof obligations before runtime confidence; executable extraction must still be tested at the system boundary.

**Verify:** build → kernel checks → targeted proofs → regression build → integration tests for extracted/runtime code.

**AI learning loop:** search existing lemmas before inventing proofs; inspect types/goals before generating tactics.

**Research:** https://lean-lang.org/ · https://leanprover-community.github.io/
