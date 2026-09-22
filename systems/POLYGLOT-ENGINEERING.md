# Polyglot Engineering

Use multiple languages when components have materially different execution, safety, ecosystem, or deployment requirements. The boundary is architecture.

## Boundary ladder
| Boundary | Use when | Cost | Contract |
|---|---|---|---|
| in-process FFI | low latency/shared memory matters | ABI/ownership complexity | FFI-safe types, lifetime/allocator/error rules |
| language binding | host ecosystem should call a specialized core | build/distribution complexity | binding API + compatibility tests |
| local process | isolation/independent lifecycle matters | process + serialization | bounded message schema |
| RPC | independent deployment matters | network/operations | versioned IDL + timeout/retry/idempotency |
| event/message | asynchronous loose coupling matters | eventual consistency | versioned event schema + delivery semantics |
| columnar data | large tabular data crosses runtimes | schema/version discipline | Arrow/Parquet contract |
| WebAssembly/WASI | portability/sandboxing matters | host/runtime constraints | interface/component contract |

Choose the least expensive boundary that provides the required isolation. Move right when failure containment, deployment independence, security isolation, or version decoupling is worth the overhead.

## Common shapes
Python host -> Rust/C++/Mojo core
TypeScript product/API -> Go/Rust service
Python/Julia research -> compiled component
Python -> CUDA/accelerator
Rust/Go service -> WebAssembly component

PyO3 supports Rust modules callable from Python and Python embedding from Rust; maturin is a common build path: https://pyo3.rs/main/
Apache Arrow exposes a cross-language C Data Interface, with a separate experimental device interface for accelerator memory: https://arrow.apache.org/docs/format/CDeviceDataInterface.html

## Boundary contract
Every cross-language call defines:
~~~text
types -> ownership -> lifetime -> errors -> cancellation -> timeout
      -> retry/idempotency -> compatibility -> observability -> tests
~~~

For FFI, define who allocates/frees memory and which ABI owns objects. For process/RPC boundaries, bound request/response size, concurrency, queueing, retries, and execution time.

## Data movement
- small control messages -> JSON/CBOR/protobuf as needed
- API/service contracts -> OpenAPI/JSON Schema/protobuf
- analytical data -> Arrow/Parquet
- native ABI -> C-compatible layout only when justified
- portable components -> WebAssembly/WASI

Avoid repeated text serialization in hot numerical paths when a typed/columnar representation can reduce copies.

## Build topology
~~~text
root/
  contracts/
  python/
  rust/
  go/
  typescript/
  native/
  integration-tests/
~~~

Each ecosystem keeps its native build/package model. The root harness orchestrates; it does not replace language tooling.

## Verification
For every boundary:
1. unit-test each side
2. build both sides
3. contract-test the interface
4. test timeout/error behavior
5. run integration tests
6. benchmark when performance matters
7. inspect boundary size and dependency changes

## Anti-patterns
language-per-function without need; shared mutable state across runtimes; stringly-typed protocols; retries hidden at multiple layers; duplicate validators with different semantics; repeated serialization in hot paths; FFI that exposes an entire runtime instead of a narrow capability.

## AI directive
Have the agent state the boundary and ownership model before generating glue. A verifier should exercise both sides independently. Parallel writers use separate worktrees.
