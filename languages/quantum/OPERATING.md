# Quantum Operating Card

**Route:** quantum algorithms, simulation, circuit research, verification experiments.

**Fast path:** select SDK/language → simulator tests → state/circuit invariants → hardware run only after simulator confidence.

**Native authority:** the selected SDK/compiler/runtime (Q#, Qiskit, Silq research implementation, etc.).

**Pair with:** Python for orchestration and numerical tooling; Rust/C++ for performance-sensitive classical support.

**Boundary:** explicit qubit/register ownership semantics, measurement behavior, numerical tolerances, simulator-vs-hardware assumptions.

**Avoid:** treating simulator behavior as hardware performance; ignoring noise/error models; unbounded shot counts.

**Reliability:** bounded experiments, seeded/reproducible simulations where possible, explicit error budgets.

**Verify:** circuit/property tests → simulator → resource estimate → hardware experiment when justified.

**AI learning loop:** establish the mathematical invariant first; code is secondary to the circuit/property specification.

**Research:** https://learn.microsoft.com/azure/quantum/ · https://www.ibm.com/quantum/qiskit
