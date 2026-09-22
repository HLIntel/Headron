# Prompt Atlas

Prompts are task interfaces. Stable rules belong in `MODEL.md`; reusable procedures belong in Skills; current facts belong in indexed docs.

## Prompt formula
`role -> task -> scope -> constraints -> tools -> output contract -> verification -> stop condition`

## Templates
- `implement.md` — implement a scoped change
- `debug.md` — reproduce and isolate a bug
- `refactor.md` — preserve behavior while changing structure
- `research.md` — gather evidence with provenance
- `security.md` — inspect trust boundaries and controls
- `performance.md` — benchmark and optimize
- `review.md` — independent code/diff review

## Compression rule
Reference files and symbols instead of pasting them. Keep constraints explicit. Ask for structured intermediate results.

## Model-specific prompts
Use short adapters for different runtimes; do not maintain parallel full prompts that can drift from `MODEL.md`.