# Qiskit Operating Card

**Route:** quantum circuit development, simulation, experiments, IBM Quantum workflows.

**Fast path:** Python environment → Qiskit → simulator/reference tests → transpilation/resource inspection → hardware experiment.

**Native authority:** current Qiskit documentation and provider/runtime API actually used.

**Pair with:** Python scientific stack; keep provider/hardware APIs behind adapters.

**Boundary:** circuit/version/provider contracts, shot limits, transpilation assumptions, noise model.

**Avoid:** unbounded shots, treating transpiled circuits as equivalent to source circuits, hiding provider-specific behavior.

**Reliability:** bounded experiments, explicit backend selection, retries with budget, result schema validation.

**Verify:** circuit tests → simulator → transpilation/resource inspection → hardware smoke test.

**AI learning loop:** inspect circuit depth/gates and transpilation before optimizing source code.

**Research:** https://www.ibm.com/quantum/qiskit · https://quantum.cloud.ibm.com/docs
