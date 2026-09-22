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