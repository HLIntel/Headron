# Hare Operating Card

**Route:** minimal native systems software with explicit control and small tooling surface.

**Fast path:** formatter/compiler → tests → debug/sanitizer tooling → target build.

**Native authority:** Hare compiler, standard library, platform ABI.

**Pair with:** C/Rust for mixed native systems; shell/Go/Python for orchestration.

**Boundary:** explicit ownership and allocation; narrow C/OS interfaces.

**Avoid:** hidden resource ownership, unchecked buffers, unnecessary abstraction.

**Reliability:** bounded memory/work queues, explicit cleanup, failure-return paths.

**Verify:** compile → tests → sanitizers/static analysis where available → target smoke test.

**AI learning loop:** read the standard library pattern first; keep patches small and auditable.

**Research:** https://harelang.org/documentation/
