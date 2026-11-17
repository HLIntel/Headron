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

## Editor and MCP
Native tooling first; the MCP layer per route is in [MCP-LANGUAGE-MATRIX.md](../../integrations/MCP-LANGUAGE-MATRIX.md). Avoid shell-execution MCP duplication when direct terminal access already exists.

## Verify
ShellCheck -> syntax -> bounded execution tests -> failure-path tests -> diff review.

## Operating card

**Route:** build glue, CI, deployment wrappers, local harnesses, diagnostics.

**Fast path:** `set -euo pipefail` where appropriate → shellcheck → shfmt → bounded commands.

**Native authority:** shell + platform utilities; document portability assumptions.

**Pair with:** Python/Go/Rust for logic that has state, parsing, concurrency, or complex error handling.

**Boundary:** quote variables, validate paths, avoid eval, use explicit temporary directories and cleanup traps.

**Avoid:** parsing JSON with grep, recursive `rm`, unbounded loops, silent error suppression, secret leakage in command output.

**Reliability:** timeouts, traps, cleanup, explicit exit codes, bounded retries.

**Verify:** shellcheck → shfmt check → dry-run where possible → CI execution.

**AI learning loop:** prefer existing project commands; do not replace robust tooling with bespoke shell parsing.

**Research:** https://www.gnu.org/software/bash/manual/ · https://www.shellcheck.net/
