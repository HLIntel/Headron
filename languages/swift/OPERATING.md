# Swift Operating Card

**Route:** Apple platforms, native components, CLI tools on macOS, value-semantic domain code.

**Fast path:** `swift-format` → `swift build` → `swift test` → sanitizers on anything with a pointer.

**Native authority:** swiftc, Swift Package Manager, XCTest and the Swift concurrency checker.

**Pair with:** Rust or C for a portable core over a C ABI; Python for tooling; TypeScript for a web surface.

**Boundary:** `Codable` plus an explicit schema at the edge; `Sendable` at every concurrency boundary, checked by the compiler rather than argued about.

**Avoid:** force unwraps on untrusted input, retain cycles in closures, `DispatchSemaphore` on an async path, unstructured `Task` with no cancellation, `@unchecked Sendable` as a silencer.

**Reliability:** structured concurrency with explicit cancellation, timeouts on every URLSession call, and strict concurrency checking left ON.

**Verify:** `swift-format` → `swift build` → `swift test` → sanitizers on anything with a pointer.

**AI learning loop:** read the types → follow one `async` call to its suspension points → make a race on purpose → test → profile with xctrace.

**Research:** https://docs.swift.org/swift-book/ · https://www.swift.org/documentation/ · https://www.swift.org/getting-started/
