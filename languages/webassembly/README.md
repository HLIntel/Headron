# WebAssembly / WASI

Status: production runtime technology with evolving component tooling.

## Purpose
Portable compiled modules, sandboxed execution, browser runtimes, server-side components, and cross-language distribution.

## Stack
Language-specific compiler/toolchain, wasm runtime, WASI/component tooling where required, bindgen/interface generation, tests, runtime profiling.

## State
Clearly distinguish linear memory, host resources, handles, and component interfaces. Keep resource ownership at the host/component boundary explicit.

## Concurrency
Use runtime-supported async/threads/workers only when the target runtime supports them. Bound tasks, memory, messages, host calls, and shutdown.

## Interop
Prefer explicit component/interface contracts. Map strings, bytes, arrays, errors, ownership, and versioning rather than leaking host runtime internals.

## Performance
Measure compilation size, startup, memory, host-call overhead, serialization, and actual workload latency.

## Security
Treat modules as untrusted unless provenance is known. Apply sandbox/permission policy at the host. Validate imports, resource access, input sizes, and execution budgets.

## Verify
compile -> interface validation -> runtime tests -> host-boundary tests -> resource-limit tests -> security review -> artifact inspection.

## Operating card

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
