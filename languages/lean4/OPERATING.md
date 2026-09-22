# Lean 4 Operating Card

**Route:** formal verification, proof-producing software, theorem proving, correctness-critical algorithms.

**Fast path:** lake project → `lake build` → focused theorem checks → `lake test` where applicable.

**Native authority:** Lean compiler, kernel, Lake, mathlib when used.

**Pair with:** Python/Rust/Go for executable systems whose critical algorithms are specified or verified in Lean.

**Boundary:** treat theorem statements and executable interfaces as contracts; minimize trusted axioms.

**Avoid:** proving irrelevant properties, opaque automation without understanding, oversized theorem dependencies.

**Reliability:** proof obligations before runtime confidence; executable extraction must still be tested at the system boundary.

**Verify:** formatter/build → kernel checks → targeted proofs → regression build → integration tests for extracted/runtime code.

**AI learning loop:** search existing lemmas before inventing proofs; inspect types/goals before generating tactics.

**Research:** https://lean-lang.org/ · https://leanprover-community.github.io/
