# WebAssembly/WASI Operating Card

**Route:** portable sandboxed components, edge/serverless execution, language interoperability.

**Fast path:** compile target → WASM validation → runtime test (Wasmtime/target host) → size/performance check.

**Native authority:** target compiler/toolchain plus WASI/runtime semantics.

**Pair with:** Rust/Go/C/C++/AssemblyScript and host languages; keep host/component boundaries explicit.

**Boundary:** capability-based imports, explicit memory ownership, ABI/component schema, bounded input/output.

**Avoid:** oversized modules, hidden host capabilities, unbounded linear-memory growth, ABI drift.

**Reliability:** capability allowlists, fuel/time budgets where supported, deterministic resource limits, versioned interfaces.

**Verify:** compile → module validation → runtime tests → host/component contract tests → size/perf regression.

**AI learning loop:** inspect imports/exports and ABI before editing implementation.

**Research:** https://webassembly.org/docs/ · https://wasi.dev/
