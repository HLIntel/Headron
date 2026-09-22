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

## VS Code + MCP
Native: language-specific WASM tooling, runtime/component tools, debugger where supported.
MCP: GitHub and Context7; semantic MCP only if the language/toolchain is supported.
Do not assume source-level semantics are proven by compilation alone.

## Verify
compile -> interface validation -> runtime tests -> host-boundary tests -> resource-limit tests -> security review -> artifact inspection.
