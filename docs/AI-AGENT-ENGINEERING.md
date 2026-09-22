# AI-Agent Engineering

AI coding systems should be treated as software operators with capabilities.

## Threat model
An agent can read files, write files, modify source, modify configuration, alter CI, install dependencies, run commands, access network resources, inspect secrets, change persistent memory, create helper scripts, and chain operations.

## Core controls
### Tool policy
Each tool needs allowed operations, denied operations, approval-required operations, path restrictions, time limits, and resource limits.

### Path fencing
Protect sensitive paths such as SSH keys, cloud credentials, secret files, credential stores, CI secrets, and system configuration.

### Sandboxing
Combine semantic policy with OS-level containment. Model instructions alone are not an enforcement boundary.

### Memory integrity
Treat persistent agent memory as a data security surface. Use write classification, versioning, content hashes, overwrite detection, deletion controls, audit logs, and recovery.

### Rollback
Use git worktrees, snapshots, copy-on-write filesystems, transactional writes, checkpointing, and replay where appropriate.

## Railguard
Repository: https://github.com/railyard-dev/railguard

Railguard is a Rust runtime for Claude Code that intercepts tool calls and applies allow, block, or ask policy decisions.

Study its command classification, pipe and evasion analysis, path fencing, content inspection, sandboxing, multi-agent coordination, snapshots, replay, recovery, memory-write policy, and content-hash integrity.

## Agent budgets
- maximum tool calls
- maximum runtime
- maximum nesting depth
- maximum files changed
- maximum bytes written
- maximum network calls
- maximum retries
- maximum queue size

## AI-generated code workflow
intent -> spec -> plan -> code -> format -> lint -> type-check -> tests -> property/fuzz -> security scan -> diff review -> policy review -> approval -> commit

Independent systems should decide whether generated code is acceptable.