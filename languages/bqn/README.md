# BQN

**Status:** research/specialized

## Purpose
Array programming, compact numerical transformations, and exploration of array-oriented problem representation.

## Core model
BQN centers arrays and uses immutable arrays as a core semantic property.

## Benefits
Can compress certain array transformations dramatically while remaining referentially transparent.

## Common mistakes
- optimizing symbol count instead of semantic clarity
- hiding business logic in dense tacit expressions
- using BQN where ordinary structured code is easier to maintain

## Streamline
Use BQN for the array transformation itself and a host language for interfaces, orchestration, persistence, and operational policy.

## AI directive
Preserve readability through comments/examples around dense array expressions. Optimize semantic compression, not textual opacity.

Official: https://mlochbaum.github.io/BQN/

## Operating card

**Route:** array programming, compact numerical transformations, alternative problem-solving models.

**Fast path:** interpreter/compiler → tiny examples → property tests against a reference implementation.

**Native authority:** chosen BQN implementation and language reference; pin implementation version for reproducibility.

**Pair with:** Python/Julia for ecosystem integration; use BQN where array semantics materially reduce algorithmic noise.

**Boundary:** explicit shape/type assumptions and conversion costs.

**Avoid:** clever glyph-heavy code without executable examples/tests; hiding expensive array copies.

**Reliability:** bounded arrays, deterministic transformations, reference-model tests.

**Verify:** reference examples → property tests → representative data benchmark.

**AI learning loop:** build a small semantic translation table before generating dense array code.

**Research:** https://mlochbaum.github.io/BQN/
