# Elixir / OTP

Purpose: fault-tolerant distributed systems, concurrent services, messaging, real-time systems, and software where supervision and failure isolation are first-class.

## When to choose Elixir
- Runtime concurrency and fault isolation matter more than raw CPU-bound throughput.
- The system benefits from OTP supervision, processes, and distributed primitives.

## Core concepts
- processes
- GenServer
- supervisors
- supervision trees
- OTP applications
- Mix

An OTP process should model runtime behavior such as mutable state, concurrency, or failure. Do not create processes merely as a code-organization trick.

Official: https://hexdocs.pm/elixir/ and https://www.erlang.org/doc/

## Reliability
Design restart behavior intentionally. A supervisor is not automatically a good recovery strategy if the state is not reconstructable or the child has an external side effect.

## Bounds
Mailbox growth, external queues, task fan-out, retries, and memory still need boundaries even though the BEAM handles process scheduling well.

## AI-specific guidance
- Let OTP handle failure domains instead of manually hiding retries in generated loops.
- Make supervision strategy explicit.
- Treat external side effects as idempotency/transaction boundaries.

## Worktree
```bash
git worktree add -b feat/elixir-task ../Code-Development-wt/elixir-task main
```