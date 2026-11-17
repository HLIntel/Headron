# Roc

**Status:** experimental

## Purpose
Functional application design, immutable data, explicit effects, and exploration of high-level reliability with native/WebAssembly targets.

## Core ideas
Roc emphasizes semantic immutability and a separation between pure and effectful functions.

## Why it matters here
It is a useful research target for understanding how language design can make mutation and effect boundaries more explicit.

## Avoid
Using current Roc tooling as though it were a fully mature general-purpose enterprise stack. The project documentation states it is not yet at a 0.1 release.

## AI directive
Ask whether a requested feature is present in the current compiler/tooling before generating code.

Official: https://www.roc-lang.org/

## Operating card

**Route:** experimental functional application development and reliability-oriented design research.

**Fast path:** pin toolchain → format/check → tests → small runtime prototype.

**Native authority:** Roc compiler/toolchain and current language/platform docs.

**Pair with:** Python/TypeScript/Go for production boundaries while Roc remains experimental.

**Boundary:** explicit platform/API contracts; keep experimental runtime assumptions isolated.

**Avoid:** treating pre-release ecosystem APIs as stable infrastructure.

**Reliability:** pure transformations where useful, explicit effects at platform boundaries, bounded resources.

**Verify:** compile/check → tests → integration prototype → runtime measurement.

**AI learning loop:** read language/platform distinction first; prefer small experiments over speculative architecture.

**Research:** https://www.roc-lang.org/
