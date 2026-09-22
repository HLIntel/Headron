# Language Atlas

Choose by workload, guarantee, and operating environment.

| Workload | Candidates | Primary decision variable |
|---|---|---|
| AI/LLM application | Python, TypeScript | ecosystem + integration speed |
| secure native core | Rust, C, Zig, C++ | ownership/safety + ABI |
| cloud/network service | Go, Rust, Elixir, Gleam | concurrency/operations |
| game/graphics/data-oriented | Odin, C++, Zig | data layout + platform APIs |
| compact native CLI/tool | Nim, Zig, Hare, Odin, V | compile/deploy model + maturity |
| scientific/quantitative | Julia, Python, F# | numerical/data ecosystem |
| GPU kernel | CUDA, Mojo, Futhark | accelerator model + data movement |
| HPC/distributed parallel | Chapel, MPI-oriented languages/tools | scale/communication model |
| functional correctness | Haskell, F#, Roc | algebraic/pure modeling |
| formal proof | Lean 4 | machine-checked specification |
| quantum | Q#, Qiskit, Silq | algorithm/tooling/hardware target |
| array/tacit computation | BQN, Uiua | data representation + expressiveness |
| C++ transition research | Carbon | C++ interoperability maturity |
| database/backend state | SQL | transaction/consistency model |
| automation glue | Bash, Python | complexity and lifecycle |
| portable component boundary | WebAssembly/WASI | sandbox/interface capability |

## Selection test
1. What is the real bottleneck?
2. What guarantee is most valuable?
3. Where is the side-effect boundary?
4. What can become unbounded?
5. What data representation dominates performance?
6. What toolchain exists on the deployment target?
7. What does the agent need to verify?
8. Can the specialized code remain behind a stable contract?

## Host/specialist model
`host application -> contract -> specialized component -> contract -> host application`

This lets Python/TypeScript/Go remain productive while Rust/C++/Mojo/Futhark/CUDA/Julia own measured specialized workloads.

## Important classification rule
SQL, Bash, CUDA, and WebAssembly are included as foundational/runtime technologies rather than pretending they are interchangeable with general-purpose application languages.