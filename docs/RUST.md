# Rust Advanced Engineering

Rust is the reference language for memory safety, systems programming, secure concurrency, and high-performance infrastructure.

## Core stack
- Tokio
- Tower
- Moka
- Governor
- Serde
- serde_json
- bytes
- secrecy
- zeroize
- proptest
- loom
- Clippy
- Miri
- cargo-audit
- cargo-deny

## Key concepts
- ownership
- borrowing
- lifetimes
- Send and Sync
- deterministic resource cleanup
- explicit unsafe boundaries
- zero-copy
- bounded async execution
- safe abstraction over unsafe internals

## Bounded async
Use semaphores, bounded channels, timeouts, cancellation, and explicit shutdown.

## Tower
Use Tower for middleware such as concurrency limits, rate limits, timeouts, load shedding, retries, and service composition.

## Moka
Use explicit capacity and expiration. Study cache stampede behavior, invalidation, ownership, and stale data.

## Secrets
Use secrecy for typed secret wrappers and zeroize for clearing sensitive values.

## Verification
- proptest for broad input classes
- loom for concurrency interleavings
- Miri for classes of undefined behavior and invalid assumptions around unsafe code

## Dependency hygiene
cargo fmt -> cargo clippy -> cargo test -> cargo audit -> cargo deny

Minimize unsafe code and document the invariants that make unsafe blocks sound.