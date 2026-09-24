# Qiskit

**Classification:** SDK and framework, **not a language route.**

Qiskit is a modular quantum software framework for circuit construction, transpilation, simulation
and execution. It is Python, so it routes as Python:

```bash
python scripts/atlas.py route path/to/circuit.py --json     # resolves to the python pack
python scripts/atlas.py plan path/to/circuit.py --task quantum --change quantum_change
```

The `quantum` task profile and the `quantum_change` gate are what make a Qiskit change different
from any other Python change: the run declares its backend, shot count, noise model and qubit
budget up front, and produces a resource estimate and a classical baseline comparison.
[The domain page](../README.md) carries both rosters.

**Why this is not a pack of its own:** its compiler, formatter, LSP and debugger would all be
Python's. A pack that restates another pack reads as coverage and gives a router nothing new to
resolve.

AI focus: keep circuit depth, backend constraints, credentials, job limits and experiment
provenance explicit. Credentials for hardware access never enter this repository.

Official: https://quantum.cloud.ibm.com/docs/
