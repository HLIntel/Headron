# CLI Engineering and Repository Harness

The CLI is the deterministic control surface. Models and IDEs should call shared repository commands rather than reimplement repository policy.

## Canonical commands
~~~text
python scripts/atlas.py check
python scripts/atlas.py route path/to/file
git status --short --branch
git diff --check
git diff --name-only
git log --oneline --decorate -20
gh pr status
gh run list
~~~

## Search
Use rg for code/text search, fd for file discovery, and fzf for interactive selection when installed. Keep grep/find as portable fallbacks in minimal scripts.

Start narrow and widen only when evidence requires it. Prefer exact files/symbols over whole-repository dumps.

## Git/GitHub
Use git for local state/worktrees; gh for interactive GitHub operations; Actions/API/Apps/MCP for integrated automation.

## Language-aware CLI
~~~text
.py      -> Ruff / Pyright / pytest
.rs      -> cargo fmt / check / clippy / test
.go      -> gofmt / vet / test / race
.ts/.tsx -> tsc / lint / test
.c/.cpp  -> compiler / sanitizers / tests / profiler
.cu      -> nvcc / profiler / kernel tests
.jl      -> Julia test / benchmark / profile
~~~

The Atlas command resolves routing; native toolchains remain authoritative.

## Environment
Keep each ecosystem's manifest and lockfile authoritative. Do not invent a universal lockfile for unrelated languages.

Optional accelerators include mise, uv, just or Task, delta, jq, and yq. Adopt only when they reduce measured friction and keep a documented portable fallback.

## Agent rule
A model should invoke shared CLI commands and consume their results. Reusable deterministic commands belong in scripts; host-specific wrappers belong in VS Code, OpenCode, Claude Code, Cursor, or other adapters.
