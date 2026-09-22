# Prompt Atlas

Prompts in this repository are engineering interfaces, not prose essays.

## Prompt structure
`role -> task -> context scope -> constraints -> tools -> output contract -> verification`

## Keep prompts short by moving stable information into:
- `MODEL.md`
- language guides
- Skills
- schemas
- tool definitions
- durable project docs

## Task templates
### Implement
State target, files/symbols, invariants, acceptance criteria, and verification.

### Refactor
State what must remain behaviorally identical, what may change, blast radius, and rollback.

### Debug
State observed behavior, expected behavior, reproduction, relevant logs, and allowed changes.

### Research
State question, source quality standard, date boundary, required evidence, and output schema.

### Security review
State asset, trust boundaries, threat surface, expected controls, and evidence required.

### Performance
State workload, baseline, metric, hardware/runtime, target, and benchmark method.

## Compact prompt rule
Reference files rather than pasting their contents. Use structured output rather than narrative when handing results between agents.