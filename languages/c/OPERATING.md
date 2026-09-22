# C Operating Card

**Route:** kernels, embedded, OS/runtime boundaries, FFI, minimal native dependencies.

**Fast path:** compiler warnings → clang-format → static analysis → unit tests → sanitizers/fuzzing.

**Native authority:** compiler, libc/platform ABI, debugger, sanitizers.

**Pair with:** Rust/C++ for safer higher-level native components; Python/Go for orchestration.

**Boundary:** every pointer has documented ownership/lifetime; every buffer has a size; ABI/version assumptions are tested.

**Avoid:** unchecked string/buffer operations, implicit ownership, integer overflow assumptions, global mutable state.

**Reliability:** explicit cleanup paths, bounds checks, watchdog/timeout behavior, deterministic resource release.

**Verify:** warnings-as-errors → tests → ASan/UBSan/TSan where applicable → fuzzing → cross-target build.

**AI learning loop:** trace pointer lifetime and error paths before changing code; do not “fix” warnings by suppressing them.

**Research:** https://www.iso.org/standard/82075.html · https://clang.llvm.org/docs/
