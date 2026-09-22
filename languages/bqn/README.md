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