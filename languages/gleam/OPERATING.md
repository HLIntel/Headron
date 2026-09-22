# Gleam Operating Card

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
