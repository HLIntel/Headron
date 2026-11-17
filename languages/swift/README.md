# Swift

**Status:** production

## Purpose
Apple-platform applications and native components where value semantics, ARC and a strict concurrency model are the point.

## Why this route exists
It fills Apple platforms and the ARC memory model, which no other route covered.

## Stack
swift package -> swift-format -> swiftc -> swift test -> sanitizers -> xctrace.

## Common mistakes
- force unwrapping a value that came from outside the process
- a strong reference cycle in an escaping closure
- blocking an async context with a semaphore
- `@unchecked Sendable` used to silence the compiler rather than to state a proof
- an unstructured `Task` with no cancellation owner

The avoid list, boundary contract, verify loop and learning loop live in the [operating card](#operating-card) below.

Official: https://www.swift.org/documentation/

## Operating card

**Route:** Apple platforms, native components, CLI tools on macOS, value-semantic domain code.

**Fast path:** `swift-format` → `swift build` → `swift test` → sanitizers on anything with a pointer.

**Native authority:** swiftc, Swift Package Manager, XCTest and the Swift concurrency checker.

**Pair with:** Rust or C for a portable core over a C ABI; Python for tooling; TypeScript for a web surface.

**Boundary:** `Codable` plus an explicit schema at the edge; `Sendable` at every concurrency boundary, checked by the compiler rather than argued about.

**Avoid:** force unwraps on untrusted input, retain cycles in closures, `DispatchSemaphore` on an async path, unstructured `Task` with no cancellation, `@unchecked Sendable` as a silencer.

**Reliability:** structured concurrency with explicit cancellation, timeouts on every URLSession call, and strict concurrency checking left ON.

**Verify:** the fast path above, every step.

**AI learning loop:** read the types → follow one `async` call to its suspension points → make a race on purpose → test → profile with xctrace.

**Research:** https://docs.swift.org/swift-book/ · https://www.swift.org/documentation/ · https://www.swift.org/getting-started/
