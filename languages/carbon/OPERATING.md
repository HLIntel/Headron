# Carbon Operating Card

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
