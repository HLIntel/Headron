# VS Code Engineering Integration

Visual Studio Code is the interactive engineering workbench in the Atlas. It is not the compiler, debugger implementation, package manager, CI system, or security boundary itself. Those remain language/runtime/toolchain responsibilities.

Official docs: https://code.visualstudio.com/docs/

## Role map

| Need | VS Code contribution | Authority |
|---|---|---|
| code editing | editor, refactors, multi-file navigation | language tools/compiler |
| code navigation | IntelliSense, symbols, definition/reference search | language server/language extension |
| debugging | breakpoints, call stack, variables, watches, launch/attach UI | debug adapter/runtime |
| testing | Test Explorer/run/debug integration where supported | test runner |
| formatting/linting | editor integration and task commands | formatter/linter |
| profiling | profiler UI/extensions/terminal integration | profiler/runtime |
| build | tasks/terminal | compiler/build system |
| Git/GitHub | source control, diffs, branches, PR workflows via extensions | Git/GitHub |
| parallel commands | Tasks with independent dependencies | OS/process/runtime |
| parallel coding | multi-root workspace + separate worktrees | Git/worktree policy |
| remote development | SSH, WSL, Dev Containers, Codespaces | remote host/container |
| AI | models, custom agents, MCP, tools | configured provider + permissions |
| enforcement | task/settings convenience | CI/rulesets/policy |

VS Code documents broad language support and can provide completion, linting, navigation, debugging, and refactoring through language extensions. citeturn854588search0turn854588search15

## Debugger layer

VS Code's debugger UI is useful because it standardizes the human inspection loop across languages: breakpoints -> call stack -> locals/watch -> step -> exception -> terminal/logs -> fix -> regression test. More complex projects use `.vscode/launch.json` to define launch/attach configurations. citeturn669231search11

Treat the debugger as an adapter over the real runtime debugger. Examples:
- Python -> Python Debugger/debugpy
- Go -> Go extension + Delve
- C/C++ -> C/C++ tooling plus the platform/compiler debugger
- JavaScript/TypeScript/Node -> built-in JS/TS/Node debugging
- Rust -> rust-analyzer for language intelligence plus a compatible native debugger extension/runtime

Go's official VS Code integration uses gopls for language intelligence and Delve for debugging. Python's current integration uses the Python Debugger extension with debugpy. citeturn854588search3turn504672search0

For remote/containerized services, prefer debugger attach over exposing debugger ports publicly. VS Code documents remote debugging through SSH/remote environments; bind and tunnel debugger endpoints securely. citeturn504672search0turn854588search11

## Language role

Do not create a second language atlas inside VS Code.

Use:
`file extension -> language guide -> toolchain -> VS Code adapter`

VS Code is the common interaction layer; the repo's language guides remain canonical for:
- compiler/build system
- package manager
- language server
- formatter/linter
- test runner
- race/concurrency detector
- sanitizer/fuzzer
- profiler
- dependency/security tooling
- native/FFI toolchain

This lets Python, Rust, Go, C/C++, Zig, Julia, F#, and the experimental/specialized languages share a workbench without pretending their toolchains are interchangeable.

## Tooling

Use the integrated terminal for commands that need exact CLI semantics. Use Tasks to turn stable commands into named entry points. Use launch configurations for reproducible debug targets. Keep task/launch inputs bounded and avoid embedding credentials.

VS Code Tasks support composed dependencies; when multiple tasks are listed in `dependsOn`, they run in parallel by default. Use this for independent checks such as contract validation + Git status, not for application concurrency semantics. `dependsOrder: sequence` is available when ordering is required. citeturn669231search8

## Parallel development

There are three distinct forms of parallelism:

1. **Parallel commands**: VS Code Tasks can run independent processes concurrently.
2. **Parallel projects**: multi-root workspaces expose multiple folders/repositories in one UI.
3. **Parallel agents/worktrees**: OpenCode/Hermes/other agent runtimes should use isolated Git worktrees when multiple writers may touch the same repository.

Do not confuse these with application concurrency. Goroutines, async tasks, BEAM processes, GPU kernels, worker pools, and distributed jobs belong in the language/runtime guides.

VS Code multi-root workspaces support multiple active repositories and workspace-scoped tasks. citeturn669231search0

## VS Code + OpenCode

Recommended division:
`OpenCode agent workspace -> implementation/exploration -> Git worktree -> VS Code -> inspect/debug/test/diff -> verification -> commit/PR`

Use the same worktree when one actor owns the write surface. Use separate worktrees when agent and human work in parallel.

When the runtime supports an attachable debugger, OpenCode can launch the process and VS Code can attach to it. This is especially useful for long-running services, workers, remote processes, or agent-generated code that is difficult to diagnose from terminal logs alone. Python's debugger, for example, supports attach workflows. citeturn504672search0

## Remote development

VS Code can work against SSH hosts, WSL, Dev Containers, and GitHub Codespaces. The remote environment carries the runtime/toolchain while the local client provides the workbench. Codespaces can configure source, compiler, debugger, extensions, and other development tooling from the repository environment. citeturn854588search1turn854588search2turn854588search6

This fits the Atlas rule:
`editor location != execution location`

Use remote execution when local hardware, OS, dependency isolation, GPU access, or environment parity makes it preferable.

## AI, MCP, and agents

VS Code can host language models, custom agents, and MCP servers. Custom agents can have task-specific tools and handoffs; MCP connects agents to external tools/services. BYOK can expose additional providers or local models. citeturn669231search2turn669231search5turn669231search9

Apply the same Atlas separation:
- MODEL.md -> behavioral contract
- VS Code custom agent -> narrow task procedure
- MCP -> external capability
- language server/debugger -> code intelligence/inspection
- task -> deterministic local command
- CI/ruleset/policy -> authoritative enforcement

Do not place secrets in `.vscode/*` or `.github/agents/*`. Workspace tasks are executable repository content, so review them like code. VS Code Workspace Trust exists specifically because project content and extensions can cause code execution. citeturn669231search1

## Repository configuration

Use committed VS Code files only for reproducible, low-risk workspace behavior:
- `.vscode/settings.json` -> navigation/search ergonomics
- `.vscode/tasks.json` -> bounded developer commands
- `.vscode/launch.json` -> reproducible debug entry points
- optional `.vscode/extensions.json` -> stable recommendations only
- `.github/agents/*.agent.md` -> optional thin task-specific agents
- `.mcp.json` -> portable MCP configuration without secrets

Avoid giant workspace instructions, duplicated language rules, provider secrets, hidden destructive tasks, or assumptions that every developer has identical hardware.

## Verification

VS Code can start and inspect verification, but completion still requires the repo's normal loop:
`format -> lint -> typecheck -> test -> property/fuzz -> security/dependency scans -> build/integration -> diff review`

For changes involving concurrency, memory, schemas, permissions, filesystem/network boundaries, CI, dependencies, or deployment, use the specialized toolchain and independent verification rather than relying on an editor indicator.

## Security

Workspace Trust protects against unintended code execution when opening untrusted workspaces. Tasks are shared repository configuration and can execute scripts/binaries. MCP servers also require explicit trust before use. Treat extensions, tasks, agent tools, and MCP servers as capabilities with provenance and least privilege. citeturn669231search1turn669231search5

## Official sources

- https://code.visualstudio.com/docs/
- https://code.visualstudio.com/docs/debugtest/debugging
- https://code.visualstudio.com/docs/languages/overview
- https://code.visualstudio.com/docs/debugtest/tasks
- https://code.visualstudio.com/docs/remote/remote-overview
- https://code.visualstudio.com/docs/remote/codespaces
- https://code.visualstudio.com/docs/agent-customization/mcp-servers
- https://code.visualstudio.com/docs/agent-customization/custom-agents
