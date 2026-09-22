# TypeScript / JavaScript

Purpose: typed application systems, APIs, AI products, agent/tool interfaces, and full-stack software.

## When to choose TypeScript
- UI or full-stack application code.
- AI tool orchestration and service integrations.
- Node-based APIs and developer tooling.

## Strict compiler baseline
Recommended baseline to evaluate:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

These options increase type precision. Add others based on the project's module/runtime model.

Official: https://www.typescriptlang.org/tsconfig/

## Runtime validation
Types are erased at runtime. Use Ajv or Valibot for external JSON, webhooks, tool arguments, model outputs, configuration, and API responses.

## Concurrency
Use bounded queues such as p-queue or rate/concurrency scheduling such as Bottleneck.

Always make concurrency, timeout, retry, queue, and shutdown behavior explicit.

## Node runtime
Treat filesystem, subprocess, network, and environment-variable access as capability boundaries.

Prefer narrow modules around side effects rather than letting arbitrary application code call subprocesses or mutate process-wide state.

## Performance
Use Node profiling and benchmarks before changing data structures or async architecture.

Watch event-loop blocking, synchronous filesystem work, huge JSON parsing, promise fan-out, and memory-retaining closures.

## AI-specific guidance
- Parse tool outputs through schemas.
- Avoid `any` at tool/API boundaries.
- Do not use `Promise.all` over arbitrary unbounded input when the workload can become large.
- Put subprocess and filesystem operations behind policy-controlled functions.

## Worktree
```bash
git worktree add -b feat/ts-task ../Code-Development-wt/ts-task main
```

Docs: https://www.typescriptlang.org/