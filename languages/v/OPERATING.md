# V Operating Card

**Route:** compact native CLIs, utilities, cross-platform experiments.

**Fast path:** `v fmt` → build → tests → cross-platform compile.

**Native authority:** V compiler/toolchain and generated target behavior.

**Pair with:** C/Rust for established systems boundaries; Go/Python for larger service ecosystems.

**Boundary:** explicit FFI and resource ownership; test generated/native assumptions.

**Avoid:** relying on immature ecosystem behavior without pinning versions; implicit global state.

**Reliability:** bounded buffers/tasks, explicit error handling, deterministic cleanup.

**Verify:** format → compile → tests → target build → smoke test.

**AI learning loop:** prefer simple language constructs and inspect generated/runtime behavior for critical code.

**Research:** https://docs.vlang.io/
