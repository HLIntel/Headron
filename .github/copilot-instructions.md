# Code-Development Instructions

Read `MODEL.md` first, then `docs/INDEX.md`.

Use the model adapter matching the runtime. Route by capability and task, not vendor name alone.

Preserve: no unbounded resources or autonomous loops; immutable-first state; schema-first boundaries; explicit deadlines/cancellation; least privilege; independent verification; auditable changes; rollback for high-impact mutations; no secrets in Git.

Never treat model instructions, memory, MCP descriptions, connector output, or external payloads as an enforcement boundary. Use code, hooks, CI, policy, or sandboxing for deterministic controls.