# Orchestrator adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to an orchestrating runtime — how the atlas is loaded
here, and the mistake this runtime makes.

## What an orchestrator is for

`tool_orchestration`, per `atlas.yaml/model_routes`: calling other agents and tools in sequence
and holding the budget. It is the runtime most able to spend a great deal and produce nothing, so
the constraints matter more here than the capabilities.

## The four that are not optional

1. **One door.** Every agent is reached the same way, so a pipeline composes without special
   cases.
2. **A budget that kills.** Every delegated run carries a deadline and dies at it. A hung agent
   looks exactly like a working one from outside, so the timer must be external to it.
3. **A ledger, not a log.** Append the agent, the exit code, the duration and the working
   directory, so a sibling process can see what was spent without reading prose.
4. **Re-anchor every claim to the instrument.** Never verify one agent against another agent's
   summary — the second agent inherits the first one's error and adds confidence to it.

## The mistake it makes

**Treating a subagent's answer as evidence.** It is a hypothesis until the native toolchain or an
instrument here confirms it. The verification bandwidth of the operator is the real scaling limit,
not the number of agents.
