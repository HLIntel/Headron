# Nim Operating Card

**Route:** compiled automation, CLIs, native services, rapid systems tooling.

**Fast path:** `nimble`/project config → formatter/linter → tests → native profiling.

**Native authority:** Nim compiler, package manager, generated C/C++/JS boundary where used.

**Pair with:** C/Rust for mature native boundaries; Python for ecosystem-heavy data/AI; SQL for persistence.

**Boundary:** generated-code assumptions are tested; macros/templates stay local and documented.

**Avoid:** macro-heavy architecture, implicit ownership assumptions, unchecked FFI, dependency sprawl.

**Reliability:** explicit buffers, timeouts, bounded workers/queues, deterministic cleanup.

**Verify:** compile with warnings → tests → static analysis → target build → benchmark.

**AI learning loop:** inspect generated/native behavior when using macros; keep abstractions smaller than the problem.

**Research:** https://nim-lang.org/docs/ · https://nim-lang.org/documentation.html
