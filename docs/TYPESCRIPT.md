# TypeScript and JavaScript Advanced Engineering

TypeScript is the reference for AI-facing applications, APIs, tool interfaces, and large typed application systems.

## Core stack
- TypeScript strict mode
- Ajv
- Valibot
- Immutable.js
- Immer
- p-queue
- Bottleneck
- ESLint
- typescript-eslint

## Boundary typing
External data should flow from unknown -> runtime validation -> trusted type -> business logic.

TypeScript types disappear at runtime. Ajv or Valibot should validate network, webhook, configuration, JSON, LLM, and third-party API inputs.

## Immutability
Use readonly types for API intent, Immutable.js for persistent immutable structures where justified, and Immer for controlled copy-on-write state updates.

## Bounded work
Use p-queue or Bottleneck with an explicit concurrency or rate limit. Do not depend on an unlimited default for production work.

Define queue capacity, timeout, retry budget, shutdown behavior, and rejection behavior.

## AI applications
Tool inputs and model outputs should pass schema validation before they reach side-effecting code.