# IDE Engineering Integration

The IDE is the interactive engineering workbench. It is not the compiler, debugger implementation,
package manager, CI system, or security boundary. Those remain language, runtime, and toolchain
responsibilities. Headron routes files to the right toolchain; the IDE surfaces the result.

## Role map

| Need | IDE contribution | Authority |
|---|---|---|
| code editing | editor, refactors, multi-file navigation | language tools / compiler |
| code navigation | symbols, definition / reference search | language server / extension |
| debugging | breakpoints, call stack, variables, watches, launch / attach UI | debug adapter / runtime |
| testing | test runner integration where supported | test runner |
| formatting / linting | editor integration and task commands | formatter / linter |
| profiling | profiler UI / terminal integration | profiler / runtime |
| build | tasks / terminal | compiler / build system |
| version control | diffs, branches, PR workflows | Git |
| parallel commands | tasks with independent dependencies | OS / process / runtime |
| parallel coding | multi-root workspace + separate worktrees | Git / worktree policy |
| remote development | SSH, WSL, containers, hosted environments | remote host / container |
| AI / agents | models, MCP, custom agents | configured provider + permissions |
| enforcement | task / settings convenience | CI / rulesets / policy |

## Headron in the IDE

```bash
python scripts/atlas.py port <file> --frame agent   # route, tier, gates, lessons
python scripts/atlas.py gate <file> <gate>          # cheapest answer for one gate
python scripts/atlas.py check                       # contract validity
python scripts/verify.py                            # full done-set
python scripts/atlas.py doctor --json               # environment health
python scripts/atlas.py failures                    # mistake ledger
python scripts/branchstate.py --land                # land a branch
```

Tasks in `.vscode/tasks.json` wire these as named IDE entry points. The default build task runs
`atlas.py check`; the verify task runs the full done-set.

## Debugger layer

The debugger UI standardizes the inspection loop across languages:
`breakpoints → call stack → locals / watch → step → exception → terminal / logs → fix → regression test`

Treat the debugger as an adapter over the real runtime debugger:
- Python → debugpy
- Go → Delve
- C / C++ → platform / compiler debugger
- JavaScript / TypeScript / Node → built-in JS debug
- Rust → native debugger extension

For remote or containerized services, prefer attach over exposing debugger ports. Bind and tunnel
endpoints securely.

## Language role

Do not create a second language atlas inside the IDE.

Use: `file extension → language guide → toolchain → IDE adapter`

The IDE is the common interaction layer; language guides remain canonical for:
compiler, build system, package manager, language server, formatter, linter, test runner,
concurrency detector, sanitizer, profiler, dependency / security tooling, native / FFI toolchain.

This lets every supported language share a workbench without pretending their toolchains are
interchangeable.

## Parallel development

Three distinct forms:

1. **Parallel commands** — tasks running independent processes concurrently.
2. **Parallel projects** — multi-root workspace exposing multiple repositories in one UI.
3. **Parallel agents / worktrees** — agent runtimes use isolated Git worktrees when multiple
   writers may touch the same repository simultaneously.

Do not confuse these with application concurrency. Goroutines, async tasks, worker pools, and
distributed jobs belong in the language / runtime guides.

## Agent integration

Recommended division:
`agent workspace → implementation / exploration → Git worktree → IDE → inspect / debug / test / diff → verification → commit / PR`

Use the same worktree when one actor owns the write surface. Use separate worktrees when agent and
human work in parallel.

When the runtime supports an attachable debugger, an agent can launch the process and the IDE can
attach. This is useful for long-running services, workers, or agent-generated code difficult to
diagnose from terminal logs alone.

## Remote development

The IDE can work against SSH hosts, WSL, containers, and hosted cloud environments. The remote
environment carries the runtime and toolchain while the local client provides the workbench.

Rule: `editor location ≠ execution location`

Use remote execution when local hardware, OS, dependency isolation, GPU access, or environment
parity makes it preferable.

## AI, MCP, and agents

The IDE can host language models, custom agents, and MCP servers. Apply the Atlas separation:

- `atlas.yaml` → behavioral contract
- custom agent → narrow task procedure
- MCP → external capability (profile-scoped; see `integrations/MCP-PROFILES.md`)
- language server / debugger → code intelligence / inspection
- task → deterministic local command
- CI / ruleset / policy → authoritative enforcement

Do not place secrets in committed IDE config files. Workspace tasks are executable repository
content — review them like code.

## Repository configuration

Commit only reproducible, low-risk workspace behavior:
- `settings.json` → navigation / search ergonomics and file associations
- `tasks.json` → bounded developer commands wired to Headron verbs
- `launch.json` → reproducible debug entry points
- `mcp.json.example` (copied locally, never committed) → portable profile-scoped MCP config

Avoid duplicated language rules, embedded credentials, hidden destructive tasks, or assumptions
about identical developer hardware.

## Verification

The IDE can start and inspect verification, but completion requires the repo's normal loop:
`format → lint → typecheck → test → property / fuzz → security / dependency scans → build / integration → diff review`

For changes involving concurrency, memory, schemas, permissions, filesystem / network boundaries,
CI, dependencies, or deployment — use the specialized toolchain and independent verification
rather than relying on an editor indicator.

## Security

Workspace Trust protects against unintended code execution when opening untrusted workspaces.
Tasks, custom agents, and MCP servers are executable; treat them as capabilities with provenance
and least privilege. MCP servers require explicit trust before use.
