# Elixir Operating Card

**Route:** fault-tolerant distributed services, messaging, real-time systems, agent coordination.

**Fast path:** Mix → formatter → Credo/quality checks → ExUnit → property tests → observer/telemetry.

**Native authority:** BEAM/OTP supervision, processes, mailboxes, releases, telemetry.

**Pair with:** Gleam for typed BEAM application code; Rust/NIFs only for measured CPU hotspots; PostgreSQL/Redis at explicit boundaries.

**Boundary:** supervision owns failure; messages are contracts; external data is validated before entering domain state.

**Avoid:** unbounded mailboxes, long-running work inside request processes, NIFs for convenience, process spawning without lifecycle ownership.

**Reliability:** supervision trees, bounded work, backpressure, restart strategy, telemetry, graceful release handling.

**Verify:** format → compile/warnings → ExUnit → property tests → integration/failure tests.

**AI learning loop:** understand supervision topology before editing process behavior; test failure and restart semantics, not only happy paths.

**Research:** https://hexdocs.pm/elixir/ · https://www.erlang.org/doc/system_principles/users_guide.html
