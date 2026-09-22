# Zig Operating Card

**Route:** low-level tools, allocators, embedded, native utilities, C replacement experiments.

**Fast path:** `zig fmt` → `zig build`/`zig test` → debug build → release benchmark.

**Native authority:** Zig compiler, build system, allocator model, `comptime`, cross-compilation.

**Pair with:** C ABI, Rust components, WASM, or higher-level orchestration languages.

**Boundary:** allocator ownership is explicit; document who allocates/frees; keep C ABI surfaces narrow.

**Avoid:** global allocators, hidden ownership assumptions, unchecked casts, compile-time metaprogramming that obscures behavior.

**Reliability:** explicit allocation limits, error unions, bounded buffers, deterministic cleanup, platform-aware tests.

**Verify:** format → build → tests → sanitizer/debug build where applicable → cross-target compile.

**AI learning loop:** inspect allocator/ownership flow first; prefer explicit data flow over clever `comptime` machinery.

**Research:** https://ziglang.org/documentation/ · https://ziglang.org/documentation/master/
