# TypeScript Operating Card

**Route:** web, full-stack, edge, SDKs, orchestration, developer tooling.

**Fast path:** package manager lockfile → `tsc --noEmit` → ESLint/Biome → Vitest → Playwright when browser behavior matters.

**Native authority:** TypeScript compiler + runtime (Node/Bun/Deno) actually hosting the artifact.

**Pair with:** Rust/WASM for CPU-heavy browser/native paths; Go/Rust for durable backend services.

**Boundary:** runtime schemas at network/DB/model boundaries; never equate TypeScript types with runtime validation.

**Avoid:** `any`, ambient global mutation, floating promises, recursive retries, unbounded event listeners, giant barrel exports, duplicate runtime/schema models.

**Reliability:** AbortSignal/deadlines, bounded concurrency, idempotent handlers, explicit HTTP status contracts.

**Verify:** typecheck → lint → unit/property tests → endpoint tests → Playwright for UI/critical flows.

**AI learning loop:** locate owning module → follow runtime boundary → inspect types + tests → smallest edit → typecheck before broad test.

**Research:** https://www.typescriptlang.org/docs/ · https://nodejs.org/docs/latest/api/
