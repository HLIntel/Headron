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

The avoid list, boundary contract, verify loop and learning loop live in `OPERATING.md` beside this guide.

Official: https://www.swift.org/documentation/
