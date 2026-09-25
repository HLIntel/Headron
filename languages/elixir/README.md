# Elixir / OTP

**Status:** production

## Purpose
Fault-tolerant concurrent services, messaging, real-time systems, supervision, and distributed workloads.

## Stack
Mix -> OTP supervision -> ExUnit -> Credo/Dialyzer where used -> Telemetry -> Broadway/GenStage-style pipelines where justified -> Nx for numerical/ML workloads where appropriate.

## Core model
Processes isolate state and communicate via messages. OTP supervisors make failure domains explicit.

## Bounds
BEAM concurrency does not remove the need to bound mailbox growth, external calls, queues, retries, memory-heavy messages, and scheduled work.

## Common mistakes
- too many processes for trivial code
- unbounded mailbox growth
- restarting state that is not reconstructable
- hidden retries
- blocking NIF/native work

## Streamline
Use OTP primitives rather than inventing custom supervision/restart frameworks.

## Performance
Measure reductions, scheduler pressure, message volume, binary memory, mailbox sizes, and native bottlenecks.

## AI directive
Ask what the supervision tree is, what state is reconstructable, and what happens after restart before generating new processes.

## Verify
`mix format --check-formatted`, tests, static/dialyzer checks where configured, integration tests, and failure/restart tests.

Official: https://hexdocs.pm/elixir/
