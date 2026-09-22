# Rust

Purpose: memory-safe systems programming, infrastructure, security-sensitive code, native tooling, high-performance services, and performance-critical AI infrastructure.

## When to choose Rust
- Need strong compile-time ownership/aliasing guarantees.
- Need predictable resource management and native performance.
- Need a secure boundary around unsafe/C/FFI code.

## Core stack
- Cargo
- Tokio
- Tower
- Serde
- Moka
- Governor
- bytes
- secrecy
- zeroize
- proptest
- loom
- Clippy
- Miri
- cargo-audit
- cargo-deny

## Workspace design
Use Cargo workspaces for related crates.

```toml
[workspace]
resolver = "3"
members = ["crates/*", "apps/*"]
```

Keep dependency versions and shared policy centralized when appropriate. Use `cargo check --workspace` and `cargo test --workspace` for repository-level verification.

Official: https://doc.rust-lang.org/cargo/reference/workspaces.html

## Safety
Prefer safe Rust. Isolate `unsafe` into small modules with explicit safety invariants and focused tests.

## Concurrency
Tokio does not automatically bound your workload. Add semaphores, bounded channels, timeouts, cancellation, and graceful shutdown.

Tower is useful for middleware such as timeout, concurrency limits, rate limits, and load shedding.

## Performance
Use release profiles, benchmarks, criterion-style measurement, allocation analysis, and CPU profiling before optimizing.

Prefer zero-copy or borrowed data only when it materially reduces cost and does not make correctness harder.

## Cache
Use Moka when a concurrent bounded cache is actually required. Specify capacity, expiry, and invalidation.

## Verification
```bash
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo check --workspace
cargo test --workspace
cargo audit
cargo deny check
```

Use Miri and loom for targeted advanced verification rather than every test run.

## AI-specific guidance
- Prefer compiler-guided implementation over large generated rewrites.
- Ask the compiler to expose ownership mistakes early.
- Treat unsafe, FFI, build scripts, and dependency changes as elevated-risk edits.

## Worktree
```bash
git worktree add -b feat/rust-task ../Code-Development-wt/rust-task main
```

Docs: https://www.rust-lang.org/ and https://doc.rust-lang.org/