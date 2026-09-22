# C++ Operating Card

**Route:** engines, graphics, HPC, embedded, mature native ecosystems.

**Fast path:** CMake/Bazel → clang-format → clang-tidy → compiler warnings-as-errors → tests → sanitizers/fuzzing.

**Native authority:** compiler, standard library, build system, debugger, sanitizers.

**Pair with:** Rust for safer new native boundaries; Python/TypeScript for product/control planes; CUDA for GPU kernels.

**Boundary:** RAII, ownership types/conventions, narrow ABI, explicit serialization/versioning.

**Avoid:** raw owning pointers, exception/error ambiguity, giant templates, global state, data races, unchecked casts.

**Reliability:** RAII cleanup, bounded threads/queues, deadlines, explicit shutdown, ASan/UBSan/TSan where supported.

**Verify:** format → compile warnings-as-errors → tests → sanitizers → fuzz → benchmark.

**AI learning loop:** identify ownership and lifetime before editing; treat templates/macros/build files as high-context surfaces.

**Research:** https://isocpp.org/ · https://en.cppreference.com/
