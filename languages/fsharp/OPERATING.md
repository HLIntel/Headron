# F# Operating Card

**Route:** typed .NET services, data processing, domain-heavy applications, quantitative code.

**Fast path:** `dotnet restore` → formatter/analyzers → `dotnet test` → property tests → profiler.

**Native authority:** .NET SDK, F# compiler, FSharp.Core, debugger, analyzers.

**Pair with:** C#/F# on .NET boundaries; Python for ML; Rust/C++ for selected native workloads.

**Boundary:** discriminated unions and records for domain contracts; validate external JSON/HTTP before conversion.

**Avoid:** null-heavy interop, mutable shared state, unnecessary object allocation in hot loops.

**Reliability:** async workflows with cancellation, bounded concurrency, explicit database transactions.

**Verify:** build/analyzers → tests → property tests → integration → benchmark.

**AI learning loop:** identify domain types first; use pattern matching to make invalid states harder to represent.

**Research:** https://learn.microsoft.com/dotnet/fsharp/ · https://fsharp.org/
