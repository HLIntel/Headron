# Gleam

**Status:** production-specialized

## Purpose
Typed functional systems on the BEAM, message-oriented services, and fault-tolerant applications with Erlang/Elixir interoperability.

## Stack
Gleam compiler/toolchain -> `gleam format`/`check`/`test` -> Hex packages -> OTP/Gleam Actors -> Erlang/Elixir interop.

## Core model
Immutable data plus typed interfaces make many application-level states easier to reason about. Gleam OTP Actor abstractions provide typed message-oriented concurrency.

## Bounds
Bound external calls, queues, mailbox growth, retries, and large messages.

## Common mistakes
- assuming BEAM scalability makes every loop safe
- allowing mailbox growth
- overusing actors for purely local computation
- treating type safety as a substitute for runtime input validation

## Streamline
Use simple functional transformations and OTP supervision rather than bespoke concurrency frameworks.

## AI directive
Use actors where a real state/concurrency boundary exists. Validate external data before entering the actor state machine.

## Verify
`gleam format --check`, `gleam check`, `gleam test`, integration tests against BEAM dependencies.

Official: https://gleam.run/

## Operating card

**Route:** typed BEAM services, reliable messaging, distributed coordination.

**Fast path:** `gleam format` → `gleam check` → `gleam test` → BEAM runtime inspection.

**Native authority:** Gleam compiler/tooling plus Erlang/OTP runtime.

**Pair with:** Elixir/OTP libraries, Rust only through carefully isolated native boundaries, SQL/Redis via explicit adapters.

**Boundary:** typed domain messages, validated external data, explicit actor/process ownership.

**Avoid:** hiding side effects, oversized processes, unbounded mailboxes, FFI without lifecycle tests.

**Reliability:** supervision, backpressure, bounded concurrency, restart semantics, telemetry.

**Verify:** format → check → tests → property/integration tests → failure/restart scenarios.

**AI learning loop:** use types and compiler errors as navigation; inspect generated/runtime behavior before abstractions.

**Research:** https://gleam.run/documentation/ · https://www.erlang.org/doc/system_principles/users_guide.html
