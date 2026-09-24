# Swift

**Status:** production

## Purpose
Apple-platform applications and native components where value semantics, ARC and a strict concurrency model are the point.

## Why this route exists
It fills Apple platforms and the ARC memory model, which no other route covered. A language earns a route here only by contributing a distinct guarantee,
runtime property, ecosystem or performance characteristic — not by being popular.

## Stack
swift package -> swift-format -> swiftc -> swift test -> sanitizers -> xctrace.

## Common mistakes
- force unwrapping a value that came from outside the process
- a strong reference cycle in an escaping closure
- blocking an async context with a semaphore
- `@unchecked Sendable` used to silence the compiler rather than to state a proof
- an unstructured `Task` with no cancellation owner

## AI directive
Force unwraps on untrusted input, retain cycles in closures, `dispatchsemaphore` on an async path, unstructured `task` with no cancellation, `@unchecked sendable` as a silencer — check for these before generating code, and state the
boundary contract (`Codable` plus an explicit schema at the edge; `Sendable` at every concurrency boundary, checked by the compiler rather than argued about) before writing the logic that crosses it.

## Verify
`swift-format` → `swift build` → `swift test` → sanitizers on anything with a pointer

## Learn into
read the types → follow one `async` call to its suspension points → make a race on purpose → test → profile with xctrace

Official: https://www.swift.org/documentation/
