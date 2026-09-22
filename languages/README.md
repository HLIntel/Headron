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

## Language index

<!-- BEGIN generated: language-index (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/artifact_routes` — 29 routes, 2 tool manifests. Do not hand-edit; `check` fails on drift.

| route | guide | operating card | tool manifest |
|---|---|---|---|
| `quantum` | [guide](quantum/README.md) | [card](quantum/OPERATING.md) | none |
| `bash` | [guide](bash/README.md) | [card](bash/OPERATING.md) | none |
| `bqn` | [guide](bqn/README.md) | [card](bqn/OPERATING.md) | none |
| `c` | [guide](c/README.md) | [card](c/OPERATING.md) | none |
| `carbon` | [guide](carbon/README.md) | [card](carbon/OPERATING.md) | none |
| `chapel` | [guide](chapel/README.md) | [card](chapel/OPERATING.md) | none |
| `cpp` | [guide](cpp/README.md) | [card](cpp/OPERATING.md) | none |
| `cuda` | [guide](cuda/README.md) | [card](cuda/OPERATING.md) | none |
| `elixir` | [guide](elixir/README.md) | [card](elixir/OPERATING.md) | none |
| `fsharp` | [guide](fsharp/README.md) | [card](fsharp/OPERATING.md) | none |
| `futhark` | [guide](futhark/README.md) | [card](futhark/OPERATING.md) | none |
| `gleam` | [guide](gleam/README.md) | [card](gleam/OPERATING.md) | none |
| `go` | [guide](go/README.md) | [card](go/OPERATING.md) | none |
| `hare` | [guide](hare/README.md) | [card](hare/OPERATING.md) | none |
| `haskell` | [guide](haskell/README.md) | [card](haskell/OPERATING.md) | none |
| `julia` | [guide](julia/README.md) | [card](julia/OPERATING.md) | none |
| `lean4` | [guide](lean4/README.md) | [card](lean4/OPERATING.md) | none |
| `mojo` | [guide](mojo/README.md) | [card](mojo/OPERATING.md) | none |
| `nim` | [guide](nim/README.md) | [card](nim/OPERATING.md) | none |
| `odin` | [guide](odin/README.md) | [card](odin/OPERATING.md) | none |
| `python` | [guide](python/README.md) | [card](python/OPERATING.md) | [tools.yaml](python/tools.yaml) |
| `quantum/qsharp` | [guide](quantum/qsharp/README.md) | [card](quantum/qsharp/OPERATING.md) | none |
| `roc` | [guide](roc/README.md) | [card](roc/OPERATING.md) | none |
| `rust` | [guide](rust/README.md) | [card](rust/OPERATING.md) | [tools.yaml](rust/tools.yaml) |
| `sql` | [guide](sql/README.md) | [card](sql/OPERATING.md) | none |
| `typescript` | [guide](typescript/README.md) | [card](typescript/OPERATING.md) | none |
| `uiua` | [guide](uiua/README.md) | [card](uiua/OPERATING.md) | none |
| `v` | [guide](v/README.md) | [card](v/OPERATING.md) | none |
| `webassembly` | [guide](webassembly/README.md) | [card](webassembly/OPERATING.md) | none |
| `zig` | [guide](zig/README.md) | [card](zig/OPERATING.md) | none |
<!-- END generated: language-index -->
