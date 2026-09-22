# Languages

Use [ATLAS.md](ATLAS.md) to choose by workload. Each language has a stable overview plus a compact `OPERATING.md` card for AI/code routing.

**Language route:** `README.md → OPERATING.md → task profile → native tools → boundary tests → verification`.

| Family | Languages |
|---|---|
| Application/orchestration | Python, TypeScript |
| Systems/infrastructure | Rust, Go, C, C++, Zig, Nim, V, Hare, Odin |
| Data/accelerator/HPC | Julia, Mojo, Futhark, Chapel, CUDA |
| Functional/correctness | Haskell, F#, Elixir, Gleam, Roc, Lean 4 |
| Language research | Carbon, BQN, Uiua |
| Boundary/runtime | SQL, Bash, WebAssembly/WASI |
| Quantum | Quantum, Q#, Silq, Qiskit |

## Operating cards

Every route has an `OPERATING.md` containing its fast path, native authority, pairing strategy, boundary contract, anti-patterns, reliability practices, verification loop, AI learning loop, and primary research links. See [PACK-SPEC.md](PACK-SPEC.md).

## Cross-language practice

Use [systems/POLYGLOT-ENGINEERING.md](../systems/POLYGLOT-ENGINEERING.md) when multiple languages intentionally share one product. Define the boundary before choosing the second language.
