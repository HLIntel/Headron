# Language Mastery / AI Speed-Run Protocol

The fastest route is not reading the entire language. Build a small executable mental model, then repeatedly connect it to real repository work.

## 7-pass loop

1. **Reference:** read syntax, type/state model, concurrency model, package/build model.
2. **Trace:** find one real implementation in this repository and follow input → transformation → boundary → output.
3. **Reproduce:** implement a tiny equivalent without copying.
4. **Break:** introduce one controlled failure: invalid input, timeout, race, allocation pressure, mutation, dependency outage, or schema drift.
5. **Verify:** use the language's native compiler/test/debugger before external AI judgment.
6. **Measure:** benchmark/profile only when the workload makes performance relevant.
7. **Record:** add only the reusable lesson, command, invariant, or routing rule.

## Mastery gates

A language is operationally learned when you can explain and demonstrate:

- its ownership/state model
- its error model
- its concurrency model
- its package/build model
- its debugger/profiler path
- its dominant performance failure modes
- its boundary/FFI behavior
- its testing/property/fuzzing options
- its deployment/runtime assumptions

## AI learning rule

AI should first **retrieve and reason from the language's primary reference**, then inspect repository examples, then generate. After generation, the compiler/tester becomes the teacher. Do not let fluent output substitute for language knowledge.

## Efficiency rule

For every new tool, ask: **does it remove repeated human work, expose a hidden invariant, improve verification, or reduce context/tool calls?** If not, do not add it merely because it is available.

## Polyglot mastery

Learn one language deeply enough to understand its guarantees, then learn adjacent languages by contrast: ownership, memory, concurrency, error handling, build system, runtime, boundary costs. This produces transferable engineering skill faster than memorizing syntax independently.

## Evidence hierarchy

`language reference → compiler/runtime behavior → official examples → repository tests → benchmark → community discussion → model-generated explanation`.

Research links live in each language's `OPERATING.md` so this file remains a method rather than another documentation dump.
