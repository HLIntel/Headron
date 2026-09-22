# Rust Operating Card

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
