# Repository Consistency

Code-Development has multiple entry points for models, humans, and tools. Agreement is checked rather than assumed.

Canonical layers:

<!-- BEGIN generated: canonical-flow (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/default_flow` — the order a reader, an agent or an instrument
should consult these in.

1. `MODEL.md`
2. `docs/INDEX.md`
3. `atlas.yaml`
4. `runtime_adapter`
5. `language_guide`
6. `operating_card`
7. `tool_manifest`
8. `boundary`
9. `task_route`
10. `scoped_tools`
11. `verify`
<!-- END generated: canonical-flow -->

**The hand-written version of that list omitted the operating card and the tool manifest** —
two layers `atlas.yaml` declares — and added two files it does not. What the harness proves,
and what it does not, is declared per instrument in `atlas.yaml/instruments` and rendered in
[the README's instrument table](../README.md#instruments--what-each-one-proves-and-who-closes-what-it-does-not);
a shorter second roster here could only disagree with it.

The wiki should route to canonical repository files rather than silently replacing them.

When a dynamic entrypoint or generated file cannot be proven by static analysis, document the exception instead of weakening the global detector.
