# Rust

**Status:** production

## Purpose
Memory-safe systems, infrastructure, secure services, high-performance tooling, native components, and strict ownership boundaries.

## Use when
Compile-time ownership/aliasing guarantees, native performance, predictable resource handling, or a narrow secure systems boundary is valuable.

## Stack
Cargo workspace -> rust-analyzer -> rustfmt -> Clippy -> tests -> proptest/loom/Miri -> cargo-audit/cargo-deny.
Common runtime/service tools: Tokio, Tower, Axum, Reqwest, Serde, tracing, Moka, Governor.

## Workspace
Use a Cargo workspace for related crates. Centralize shared metadata/dependencies/lints at the workspace root where appropriate.

## State
Let ownership and borrowing express state ownership. Avoid Arc<Mutex<T>> as the first design reflex; first ask whether ownership can be moved, partitioned, or made immutable.

## Concurrency
Use structured task ownership, bounded channels, semaphores, cancellation, and shutdown. Tokio supplies runtime facilities, not automatic business-level bounds.

## Performance
Benchmark first. Measure allocations, copies, serialization, contention, syscalls, and tail latency. Use profiling and optimized builds only after a baseline.

## Common mistakes
- unnecessary cloning
- large shared locks
- unbounded channels
- retry middleware without budget
- `unsafe` for convenience
- feature/dependency sprawl

## Streamline
Keep crates small by domain, but avoid fragmentation. Use traits where they reduce coupling; avoid traits used only to look abstract.

## Learn into
ownership -> traits/generics -> async runtime -> unsafe boundaries -> profiling -> FFI.

## Avoid
unsafe without an explicit invariant, premature lock-free design, and abstraction layers that hide allocation or synchronization.

## AI directive
Let the compiler expose mistakes early. Treat `unsafe`, FFI, build scripts, proc macros, dependency changes, and concurrency primitives as elevated-risk edits.

## Verify
`cargo fmt --check`, `cargo check --workspace`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `cargo test --workspace`; targeted Miri/loom/proptest; cargo-audit/cargo-deny.

Official: https://doc.rust-lang.org/

## Operating card

**Route:** secure systems, infrastructure, native services, performance-critical libraries.

**Fast path:** Cargo workspace → rustfmt → Clippy → tests → Miri/loom/proptest where relevant.

**Native authority:** `rustc`, Cargo, rust-analyzer, Clippy, Miri, `cargo test`.

**Pair with:** Python/TypeScript at product edges; CUDA/Mojo for accelerator work; C/C++ only behind deliberate FFI boundaries.

**Boundary:** Serde schemas, explicit FFI ownership, `Send`/`Sync` reasoning, bounded channels and cancellation.

**Avoid:** `Arc<Mutex<_>>` by reflex, unnecessary cloning, unsafe convenience, hidden allocations, unbounded Tokio channels.

**Reliability:** structured task ownership, cancellation, timeouts, bounded concurrency, graceful shutdown, tracing.

**Verify:** fmt → check → Clippy `-D warnings` → tests → targeted Miri/loom/proptest → cargo-audit/cargo-deny.

**AI learning loop:** read types first; let compiler errors guide the edit; isolate unsafe/FFI/concurrency changes; verify narrowly before workspace-wide.

**Research:** https://doc.rust-lang.org/stable/ · https://doc.rust-lang.org/reference/ · https://rustc-dev-guide.rust-lang.org/
