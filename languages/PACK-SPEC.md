# Language Pack Contract

Every `languages/<route>/` is a compact operating system for that language, not a textbook.

## Required card

Each language pack should answer, in this order:

1. **Purpose** — what workload the language earns a place for.
2. **Fast path** — smallest reliable toolchain and first commands.
3. **Native authority** — compiler/runtime/package manager/LSP/debugger.
4. **Best pairings** — where another language or runtime should own adjacent work.
5. **Boundary contract** — API/schema/ABI/FFI/data/queue rules.
6. **Verification** — formatter, linter, type checker, tests, fuzz/property/mutation, security.
7. **Performance** — what to measure before optimizing.
8. **Failure/uptime** — deadlines, cancellation, retries, health/readiness, graceful shutdown.
9. **Anti-noise** — dependencies, abstractions, generated files, context, and tool calls to avoid.
10. **AI learning loop** — read → trace → modify → verify → record.
11. **Research** — official reference plus a deeper learning/research path.

## Universal route

`MODEL.md → docs/INDEX.md → atlas.yaml → language pack → task profile → native tools → focused external tool → verification → decision record`

Do not load every language pack into every model context. Load the current language card, the task profile, and only the boundary cards needed by the change.

## Multi-language rule

Use multiple languages because their *contracts* compose, not because more languages look sophisticated. Define the boundary first; then assign ownership to the language whose native guarantees reduce total system complexity.

## Anti-bloat rule

A language pack should prefer links to authoritative references over copied documentation. Put commands, invariants, failure modes, and routing decisions here; put exhaustive reference material at the upstream source.
