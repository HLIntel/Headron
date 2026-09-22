# Bash

Status: production as automation/glue.

## Purpose
CI orchestration, build scripts, deployment glue, local automation, process control, and Unix interoperability.

## Stack
Bash, ShellCheck, Bash language server, coreutils, Git, gh, jq/yq, and explicit OS commands.

## State
Avoid global mutable shell state. Quote variables, validate paths, separate data from commands, and make temporary-file cleanup explicit.

## Concurrency
Background processes require ownership, PID tracking, bounded fan-out, wait/join, timeout, and signal cleanup. Avoid uncontrolled & loops.

## Interop
Bash is a process boundary, not a typed internal API. Use machine-readable outputs and validate external data before acting.

## Performance
Prefer fewer process launches for hot loops; move substantial logic into a typed language when complexity or failure handling grows.

## Security
Treat expansion, globbing, command substitution, PATH lookup, downloaded scripts, environment variables, and untrusted command output as attack surfaces.

## VS Code + MCP
Native: terminal, ShellCheck, Bash language server.
MCP: Serena where Shell support is useful, GitHub, Semgrep.
Avoid shell-execution MCP duplication when direct terminal access already exists.

## Verify
ShellCheck -> syntax -> bounded execution tests -> failure-path tests -> diff review.
