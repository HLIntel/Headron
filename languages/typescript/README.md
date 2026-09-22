# TypeScript / JavaScript

**Status:** production

## Purpose
AI applications, APIs, full-stack systems, tool interfaces, web products, and Node-based developer tooling.

## Stack
TypeScript strict -> ESLint/typescript-eslint -> Vitest -> schema validation -> integration tests.
Boundary tools: Ajv, Valibot, Zod when appropriate. Work-control tools: p-queue, Bottleneck. Browser integration: Playwright where needed.

## Compiler discipline
Evaluate `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes` for serious codebases. Add other flags deliberately based on runtime/module needs.

## Runtime boundary
Types disappear at runtime. Validate network/webhook/LLM/tool/config input from `unknown` before use.

## Concurrency
Promise fan-out is a resource. Use queues/semaphores/schedulers with explicit concurrency, queue, timeout, retry, and shutdown behavior.

## Common mistakes
- `any` at boundaries
- Promise.all over arbitrarily large input
- synchronous filesystem/CPU work on the event loop
- shared mutable module state
- giant JSON parsing with no size policy
- spawning processes directly from arbitrary application code

## Streamline
Use discriminated unions, schema-derived types, table-driven dispatch, shared endpoint middleware, and one validation boundary.

## Performance
Profile event-loop blocking, allocations/retained closures, JSON serialization, network waits, and bundle/runtime effects before optimizing.

## Learn into
strict typing -> schema systems -> Node runtime boundaries -> async resource control -> observability -> performance.

## AI directive
Treat model output as `unknown` until validated. Generated tool interfaces must be schema-first, bounded, and side-effect-isolated.

## Verify
`npx tsc --noEmit`, lint, unit/integration tests, schema tests, security/dependency checks.

Official: https://www.typescriptlang.org/