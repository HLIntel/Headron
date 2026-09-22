# Chapel Operating Card

**Route:** distributed/HPC workloads, parallel algorithms, large-scale numerical systems.

**Fast path:** `chpl` → compiler warnings → tests → representative parallel run → performance analysis.

**Native authority:** Chapel compiler/runtime, parallel and locale model.

**Pair with:** Python for orchestration/analysis; C/C++/Fortran/CUDA for established HPC kernels.

**Boundary:** define distribution, locality, synchronization, and memory ownership explicitly.

**Avoid:** implicit data movement, unbounded parallelism, synchronization hidden inside abstractions.

**Reliability:** bounded task creation, explicit synchronization, failure-aware distributed operations.

**Verify:** compile → tests → race/data-movement checks where available → scale test → profile.

**AI learning loop:** map locality and parallel ownership before editing; benchmark at realistic scale.

**Research:** https://chapel-lang.org/docs/
