# Repository Consistency

Code-Development has multiple entry points for models, humans, and tools. Agreement is checked rather than assumed.

Canonical layers:
- MODEL.md: behavioral/control contract
- VERSION: contract version
- atlas.yaml: machine routing
- docs/INDEX.md: human routing
- language README: language detail
- model adapter: runtime translation
- wiki/: human/agent navigation overlay
- scripts/atlas.py: deterministic repository harness

The harness checks version surfaces, required files, symlinks, routes, model adapters, local Markdown links, language-guide indexing, durable-document reachability, workflow hygiene, environment-file hygiene, and whitespace.

The wiki should route to canonical repository files rather than silently replacing them.

When a dynamic entrypoint or generated file cannot be proven by static analysis, document the exception instead of weakening the global detector.
