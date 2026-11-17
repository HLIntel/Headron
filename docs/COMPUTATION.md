# Computation direction and handoff

## Goal and current boundary

Turn a structured request into a typed input, selective deterministic computation and a compact result with evidence and explicit limits. Version program definitions with the repository; expose approved capabilities through existing agent interfaces. A server process is still required, and a repository link alone does not execute code.

The [microprogram registry](../scripts/microprogram.py) dispatches named operations. [Finance and reconciliation](FINANCE.md) demonstrate decimal calculations, reference lookup and cross-domain record comparison. The quantitative analysis profile declares expected checks; it does not enforce them. [Verification](VERIFY.md) describes existing gates and their scope. None of this establishes a general computation compiler, automatic planning, distributed execution or reliable cached reuse.

The registry now exposes `compute.compose`, a versioned JSON graph whose variance nodes feed reconciliation nodes. It validates node identifiers, references and declared metric, currency and period before returning results. It previews referenced variances during validation and refuses values beyond the reconciliation input limit. Results include intermediates, execution order and caller-supplied source references; unmatched keys remain unmatched. The [implementation contract](../scripts/compute_compose.py) and [examples and refusal cases](../scripts/compute_compose_test.py) specify the input shape. Discover it through `mind --micro list`; the same registry serves agent callers. Sources, economic comparability and assumptions remain unverified.

`compute.contract` returns the machine-readable outer request shapes enforced for finance, reconciliation and composition. These declarations do not describe every nested field or guarantee that an input is economically meaningful; the individual operations enforce their detailed rules. The impact selector now treats malformed or empty recorded dependencies as work to rerun, while dynamic subprocess dependencies and external state still require wider verification.

## Ordered work

| Priority | Mechanism and next implementation | Evidence required to advance |
|---|---|---|
| In progress | Finance, reconciliation and the graph share discoverable, enforced outer request shapes; operations retain detailed validation and source labels remain assertions. | Nested cross-operation schemas, result schemas and independently reviewed assumptions remain open. |
| In progress | The graph composes variance with reconciliation and validates declared dependencies and metadata. Extend only with explicitly typed, allowlisted edges. | Broader independent end-to-end examples, resource exhaustion and partial-failure evidence; arbitrary code execution remains out of scope. |
| Next | Bind evidence and reuse to actual inputs and execution state. Resolve revisions to immutable identities and include program, input, operator version and relevant environment or external-data identity. Refuse reuse when identity or freshness is unknown. | Mutation cases for dirty files, changed inputs, dependencies and environment; compare reused results with clean recomputation. A commit alone does not identify a working tree or external data. |
| Then | Use change impact to select work conservatively, falling back to wider verification when dependencies are unknown. Search for counterexamples and report its bounds rather than presenting a search as proof. | Seeded defects covering dynamic dependencies, incomplete graphs and stale evidence; show that selection catches them against a full-run baseline. |
| Measure | Compare retrieval, composition and scheduling against existing paths on representative tasks. Optimize only after collecting latency, resource use, accuracy and failure data. | Repeatable baselines, held-out cases, uncertainty and regression thresholds; no speed or reliability claim without measurement. |

## Research map

- Claims and state: distinguish observation, derivation, assumption and unknown; track provenance, time, contradictions and invalidation. Entity identity and causal conclusions require evidence beyond matching labels.
- Agent execution: bind preconditions and permissions to observed state, verify postconditions independently, stop loops without progress, and reconcile partial effects. Concurrent work needs conflict detection and scoped authority.
- Context and memory: preserve obligations during compression, expire stale evidence and disclose only relevant routes. [Encoding](ENCODING.md) already specifies expansion and measurement constraints.
- Numerical and domain work: carry dimensions and lineage through calculations; use conservation, reconciliation and known-answer checks. Add finance, logistics or other operators only with explicit assumptions and refusal cases.
- Multimodal and physical work: coordinate frames, identity, temporal order and action limits are research candidates. Perception, simulation and real-world effects need separate evidence; a text-only check cannot establish them.
- Scheduling, hardware and learned optimization: research directions, not current capabilities. Require a measured workload and a simpler baseline before adding infrastructure or specialized hardware.

## Security and continuation

Repository contents and supplied records are untrusted. Keep operations allowlisted, enforce execution budgets and authorization at the actual boundary, and treat generated plans as data until validated. Do not infer broker access, custody, source authenticity, production readiness or legal conclusions from a computed value.

Next owner: extend the enforced contract to nested inputs and results, then test compatibility and refusal across additional edges before expanding the graph. The research attachments contain leads and proposed mechanisms; their numerical and novelty claims need primary-source verification before reuse.
