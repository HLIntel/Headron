# Language Atlas

Use this page to choose a language by problem shape, not by popularity.

| Work shape | Strong starting points | Why |
|---|---|---|
| AI/LLM orchestration | Python, TypeScript | ecosystem + integration speed |
| high-performance service | Rust, Go, C++ | native performance + deployment options |
| memory/ownership-sensitive core | Rust, Zig, C++, Hare | explicit ownership/control |
| cloud/network service | Go, Rust, Elixir/Gleam | concurrency + operations |
| game/data-oriented native | Odin, C++, Zig | layout/performance/control |
| scientific/numerical | Julia, Python, Chapel | numerical ecosystem/parallelism |
| GPU/data-parallel kernels | Mojo, Futhark, CUDA via host language | accelerator-specific execution |
| functional correctness | Haskell, OCaml, Roc, Lean 4 | purity/type/proof techniques |
| JVM service or data platform | Scala | the JVM runtime, its ecosystem and Java interop |
| Apple platform or native macOS tool | Swift | ARC, value semantics, strict concurrency checking |
| statistics and applied analysis | R, Python | CRAN/tidyverse, model diagnostics, reproducible reports |
| formal verification | Lean 4 | machine-checked proofs |
| quantum | Q#, Qiskit, Silq | quantum-language/tooling specialization |
| C++ migration research | Carbon | bidirectional C++ interoperability design |
| compact native tooling | Nim, Zig, Odin, Hare, V | small native binaries/control |
| massive actor-style concurrency | Elixir, Gleam | BEAM runtime + message-oriented systems |
| array/tacit exploration | BQN, Uiua | array-first problem representation |

## Routing questions
1. Is the bottleneck CPU, memory, I/O, network, GPU, developer time, or correctness proof?
2. Does ownership need compile-time guarantees?
3. Does the workload need structured concurrency or actor supervision?
4. Is Python/JS ecosystem leverage more important than raw runtime efficiency?
5. Is this a kernel or a whole application?
6. Is the code experimental or production?
7. What can become unbounded?
8. Where is the contract boundary?
9. How will the implementation be independently verified?

## Language switching pattern
```text
host language
  ↓ typed contract
specialized component
  ↓ typed contract
host language
```

Prefer this over a rewrite when only one computational boundary needs another language.

## Detailed guides

**This page used to list the routes by hand, and the list had gone stale** — it named 23 while the
atlas routed more, so a reader could not tell whether a missing name meant "no route" or "nobody
updated the sentence". The roster is generated from `atlas.yaml` instead:
[languages/README.md](README.md), with a guide, an operating card and a tool manifest per row.

## Candidates reviewed, and the verdict on each

**A language earns a route by contributing a distinct guarantee, runtime property, ecosystem or
performance characteristic — never by being popular, and never because a list looked short.** Eleven
candidates were reviewed together; four were added, one was rejected outright, and the rest carry
the trigger that would earn them. Recording a rejection is as useful as recording an addition: it
stops the same proposal arriving twice.

| candidate | verdict | reasoning |
|---|---|---|
| **OCaml** | **ADDED** | The ML family with an industrial native compiler and a first-class module system. A `.mli` signature is a contract the compiler enforces, which is a different guarantee from Haskell's purity or Lean's proofs. |
| **Scala** | **ADDED** | The JVM was entirely absent from the atlas — the largest production runtime with no route. Adds typed functional design on top of Java interop. |
| **Swift** | **ADDED** | Apple platforms, ARC and value semantics, with compiler-checked `Sendable` boundaries. Nothing else here reaches macOS or iOS natively. |
| **R** | **ADDED** | Statistics and the CRAN ecosystem, absent until now. Its failure shapes (unset seed, unpinned library, silent column coercion) are not Python's. |
| **Kotlin** | DEFERRED | Same runtime as Scala. Two JVM routes duplicate the runtime property without adding a second guarantee. **Trigger:** Android or Kotlin Multiplatform work, which Scala does not reach. |
| **Erlang** | REJECTED | The BEAM guarantee — supervision, message passing, hot code loading — is already routed through Elixir. Erlang adds syntax and history, not a property this atlas routes by. |
| **D** | DEFERRED | Overlaps C++, Zig and Nim on every axis used here: ownership, native binary size, C interop. **Trigger:** a workload where its compile-time function evaluation or GC-optional model is the deciding factor. |
| **Ada / SPARK** | DEFERRED | A genuine distinct guarantee: contract-based high-integrity development with a provable subset. **Trigger:** a safety-critical or certification-bound workload, where it would arrive with its own verification gate. |
| **Fortran** | DEFERRED | Array-oriented numerics and the LAPACK lineage, already served for this atlas's shapes by Julia, Chapel, Futhark and CUDA. **Trigger:** maintaining or interfacing with an existing HPC codebase. |
| **Prolog** | DEFERRED | Logic programming is the one paradigm with no route at all, which is a real gap in coverage — but no failure class here currently routes to it. **Trigger:** a constraint or rule-resolution problem stated as such. |
| **Lua** | DEFERRED | The embeddable-runtime niche, which is distinct. **Trigger:** an embedded scripting surface in this or a consuming system, where the host boundary is the thing being designed. |

**Rust, Python, Go, TypeScript and the rest already hold routes** — see the generated index.