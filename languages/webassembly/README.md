# WebAssembly / WASI

**Status:** production-specialized/runtime

## Purpose
Portable sandboxed execution, language interoperability, edge/runtime deployment, plugins, and componentized services.

## Component model
Use WIT/Component Model interfaces to define language-neutral contracts between components.

## Core practice
Treat WASM modules/components as capabilities with explicit imports/exports and resource permissions.

## Common mistakes
- assuming sandboxing replaces application authorization
- leaking too many host capabilities
- unstable interfaces
- ignoring serialization/copy cost across the component boundary

## Streamline
Keep components small, interface-driven, and host-language agnostic. Use WASI capabilities deliberately.

## AI directive
Generated component interfaces should explicitly state imports, exports, capabilities, resource limits, and error semantics.

## Verify
Compile the module/component, validate WIT/interface compatibility, run sandboxed integration tests, and test resource limits.

Official: https://component-model.bytecodealliance.org/