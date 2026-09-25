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

## The output contract is a SCHEMA here, not a sentence

A prompt that describes its output in prose is checked by whoever reads the answer. This
repository ships the shapes instead, so the check is mechanical:

- **the task an agent runs under**: [tools/agent-task.schema.json](../tools/agent-task.schema.json)
  — paths, commands, budgets, approval and acceptance, with the controls that REFUSE in
  `atlas.yaml/agent_policy`
- **what the atlas answers with**: [tools/atlas-output.schema.json](../tools/atlas-output.schema.json)
  — the route, plan and process records. Depend on those ids, never on rendered Markdown
- **the steps a named process takes**: `atlas.yaml/processes`, reachable as
  `python scripts/atlas.py process <id> --json`, including where it STOPS and when it escalates

So a prompt names the process and the schema rather than restating either. The context scope is
not a paragraph either: `atlas.py route <path> --json` returns it, and what a session is handed
before it asks anything is bounded by `context_policy/entry_paths`.

## Task templates
### Implement
State target, files/symbols, invariants, acceptance criteria, and verification.

### Refactor
State what must remain behaviorally identical, what may change, blast radius, and rollback.

### Debug
State observed behavior, expected behavior, reproduction, relevant logs, and allowed changes.

### Research
State question, source quality standard, **version boundary** (not a date — a date says when
somebody typed, a version says which tree the claim was true of), required evidence, and
output schema.

### Security review
State asset, trust boundaries, threat surface, expected controls, and evidence required.

### Performance
State workload, baseline, metric, hardware/runtime, target, and benchmark method.

## Compact prompt rule
Reference files rather than pasting their contents. Use structured output rather than narrative when handing results between agents.