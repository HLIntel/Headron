# Q# Operating Card

**Route:** quantum algorithms and Microsoft quantum development workflows.

**Fast path:** QDK/toolchain → compile → simulator tests → resource estimation → hardware only after validation.

**Native authority:** Q# compiler/QDK and current Azure Quantum documentation.

**Pair with:** Python/.NET for classical orchestration; keep quantum/classical boundary explicit.

**Boundary:** qubit lifetime, measurement, resource counts, simulator/hardware differences.

**Avoid:** assuming simulator cost equals hardware cost; unbounded shots; mixing classical and quantum state assumptions.

**Reliability:** explicit resource budgets, deterministic simulation fixtures, error/noise assumptions.

**Verify:** compile → simulator → resource estimate → integration/hardware experiment when justified.

**AI learning loop:** derive the algorithm/property first, then express the circuit; inspect resource estimates before optimization.

**Research:** https://learn.microsoft.com/azure/quantum/ · https://github.com/microsoft/qsharp
