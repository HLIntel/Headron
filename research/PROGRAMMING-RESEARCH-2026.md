# Programming and Agent Research Notes — 2026

Reviewed for the Atlas on 2026-09-22. Recheck volatile tooling details before standardizing them.

## Coding-agent context
ContextBench: https://arxiv.org/abs/2602.05892
Agent Retrieval Bench: https://arxiv.org/abs/2607.24882

Mechanism to adopt: measure context selection itself, not just final patch success. Track useful-file retrieval, context events, token cost, and exploration efficiency.

## Multilingual coding agents
SWE-PolyBench: https://arxiv.org/abs/2504.08703
Multi-SWE-bench: https://arxiv.org/abs/2504.02605

Mechanism to adopt: maintain language-diverse evaluation tasks and route verification by the language actually changed.

## Repository representation
CodeNib: https://arxiv.org/html/2607.25431
Knowledge Graph Based Repository-Level Code Generation: https://arxiv.org/abs/2505.14394

Mechanism to adopt: combine lexical, semantic, and structural views, then serve bounded source-linked context rather than dumping the whole repository.

## Heterogeneous programming
Backline: https://arxiv.org/abs/2609.09270
CASS: https://arxiv.org/abs/2505.16968

Mechanism to adopt: make execution placement, data movement, compilation, and execution verification explicit when code spans CPU/GPU/accelerators or vendors.

## Architectural governance
Thoughtworks fitness-function guidance:
https://www.thoughtworks.com/en-au/insights/articles/fitness-function-driven-development

Mechanism to adopt: turn important architecture characteristics into executable tests and pipeline gates.

## Research loop
~~~text
paper
 -> extract mechanism
 -> map to invariant
 -> prototype smallest control
 -> measure cost/false positives
 -> keep/remove
 -> record decision
~~~

Research is input, not doctrine. Promote a mechanism only after repository-specific validation.
