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
| functional correctness | Haskell, Roc, Lean 4 | purity/type/proof techniques |
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
`python`, `rust`, `go`, `typescript`, `cpp`, `zig`, `mojo`, `julia`, `elixir`, `gleam`, `nim`, `v`, `carbon`, `roc`, `odin`, `futhark`, `hare`, `haskell`, `fsharp`, `chapel`, `bqn`, `uiua`, `lean4`, and `quantum/*`.