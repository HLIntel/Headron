# Code-Development

**Repository contract: v0.8.0**

Code-Development is an advanced model-aware code-development atlas and operating system for polyglot programming, AI coding agents, IDEs, Git/GitHub workflows, MCP/connectors, data, performance, security, reliability, research, and verification.

The repository is organized for both humans and coding systems:
- **Control:** [MODEL.md](MODEL.md)
- **Machine routing:** [atlas.yaml](atlas.yaml)
- **Human navigation:** [docs/INDEX.md](docs/INDEX.md)
- **Language routing:** [languages/ATLAS.md](languages/ATLAS.md)
- **Runtime adapters:** [models/README.md](models/README.md)
- **MCP routing:** [integrations/MCP-LANGUAGE-MATRIX.md](integrations/MCP-LANGUAGE-MATRIX.md)
- **Code-development wiki:** [wiki/README.md](wiki/README.md)
- **Deterministic verification:** [scripts/atlas.py](scripts/atlas.py) and [docs/VERIFY.md](docs/VERIFY.md)

## Code-specific routing

Route from the artifact first, not from a generic language preference:

`file extension -> language guide -> native toolchain -> task route -> scoped MCP profile -> verification`

Examples:
- `.py` / `.pyi` -> Python -> Ruff/Pyright/pytest -> core-code/docs/security as required.
- `.rs` -> Rust -> rust-analyzer/Cargo/Clippy -> core-code/docs/security as required.
- `.go` -> Go -> gopls/go test/race/pprof -> core-code/docs/security as required.
- `.ts` / `.tsx` -> TypeScript -> TypeScript/Node test stack -> core-code/docs/browser/security as required.
- `.c` / `.cpp` -> C/C++ -> clangd/compiler/debugger/sanitizers -> core-code/docs/security as required.
- `.cu` -> CUDA -> NVIDIA compiler/debugger/profiler -> core-code/docs/security as required.
- `.sql` -> SQL -> database-native tooling -> database/docs/security profiles.
- `.sh` / `.bash` -> Bash -> terminal/ShellCheck/Bash LSP -> core-code/security without redundant shell-execution MCP.
- `.wat` / `.wasm` -> WebAssembly/WASI -> native compiler/runtime/component tooling -> core-code/docs as required.

Run `python scripts/atlas.py route path/to/file` for the canonical artifact route.

## Branch and worktree model

`main` is the shared contract baseline. Development should use short-lived topic branches and, when concurrency or risk warrants it, dedicated Git worktrees.

Language-scoped branches are allowed as **temporary lanes**:
`lang/<language>/<topic>`

They are not permanent language branches. This keeps one canonical atlas from splitting into drifting Python, Rust, Go, or other branch copies.

Use a language lane when work is primarily isolated to one language. Use a normal `feat/*`, `fix/*`, `research/*`, or `security/*` branch when the change crosses languages or repository-wide control surfaces.

See [docs/GIT-WORKTREES.md](docs/GIT-WORKTREES.md) and [wiki/BRANCH-WORKTREES.md](wiki/BRANCH-WORKTREES.md).

## Taxonomy

GitHub **labels** route work and issues. Repository **topics** improve discovery. Git **tags** identify contract/release points.

The planned taxonomy uses bounded namespaces such as:
`kind/*`, `lang/*`, `area/*`, `runtime/*`, `mcp/*`, `risk/*`, and `status/*`.

See [wiki/LABELS-TAGS.md](wiki/LABELS-TAGS.md) and [config/github-labels.json](config/github-labels.json).

## Design rule

Native compiler, LSP, debugger, test runner, profiler, package manager, and database tooling remain authoritative. AI models, IDE integrations, and MCP extend access and context without replacing executable evidence.

Recommended repository topics:
`programming-languages`, `polyglot`, `ai-agents`, `coding-agents`, `mcp`, `vscode`, `github`, `developer-tools`, `code-navigation`, `software-engineering`.
