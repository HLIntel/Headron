# Carbon

**Status:** experimental

## Purpose
Research and exploration of a successor-language approach to C++ with deep interoperability.

## Best use
Language design, migration experiments, C++ interoperability research, and compiler/toolchain evaluation.

## Avoid
Treating Carbon as a drop-in production replacement. It is an experiment with a stated goal of C++ interoperability, and this pack exists to study that design, not to ship on it.

## Study
- bidirectional C++ interoperability
- generics/type system
- ABI/semantic boundaries
- migration strategy
- compiler/toolchain maturity

## AI directive
Agents must distinguish design goals from implemented compiler behavior and quote the current source/spec when making claims.

Official: https://docs.carbon-lang.dev/

## Operating card

**Route:** C++ interoperability research and future systems-language evaluation.

**Fast path:** pin the project/compiler snapshot → build → tests → interoperability experiment.

**Native authority:** Carbon project toolchain and current design/reference docs.

**Pair with:** C++ for production interop experiments; Rust for production-safe new native components.

**Boundary:** treat Carbon/C++ ABI and language-evolution assumptions as experimental contracts.

**Avoid:** presenting experimental Carbon features as production guarantees; broad dependency on unstable design.

**Reliability:** isolate experiments behind adapters and feature gates; preserve a C++ fallback when needed.

**Verify:** compiler version pin → build → tests → ABI/interoperability test.

**AI learning loop:** distinguish implemented behavior from roadmap/design documents before generating code.

**Research:** https://docs.carbon-lang.dev/ · https://github.com/carbon-language/carbon-lang
