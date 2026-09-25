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
