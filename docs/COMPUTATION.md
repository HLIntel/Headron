# Computation direction, architecture, and verification runtime

## Goal and current boundary

Turn a structured request into typed input, selective deterministic computation, and a compact result with cryptographic evidence and explicit limits. Version program definitions with the repository; expose approved capabilities through existing agent interfaces. A server process is still required, and a repository link alone does not execute code.

The [microprogram registry](../scripts/microprogram.py) dispatches named operations. [Finance and reconciliation](FINANCE.md) demonstrate decimal calculations, reference lookup, and cross-domain record comparison. The quantitative analysis profile declares expected checks; it does not enforce them. [Verification](VERIFY.md) describes existing gates and their scope. The computational architecture establishes verifiable execution, bounded capacity scheduling, and machine-readable evidence without mandatory cloud dependence.

## The execution pipeline: task to proof

Deterministic change verification coordinates four sequential phases:

1. **Owe (`obligations.py extract <task> <contract>`)**
   Extracts semantic requirements from the task description and binds them to matching contracts and gate obligations. The caller learns what checks the change owes before modifying repository state.

2. **Check (`headron verify --receipt verify.json`)**
   Runs required gates across changed surfaces. Verification distinguishes four honest verdicts: `pass`, `fail`, `skip`, and `not run`. Results bind to the repository tree, input digests, and execution policy, writing a verifiable machine-readable receipt.

3. **Seal (`ronbundle.py pack <task> out.ron --receipt verify.json`)**
   Packs the task specification, artifact changes, execution telemetry, and verification receipt into an immutable digest-addressed [.ron bundle](HEADRON-LANGUAGE.md#what-a-finished-program-carries-the-ron-bundle). Tampering with artifacts or receipts invalidates the bundle hash.

4. **Trust (`headron mind --micro ron.verify out.ron`)**
   Downstream systems, automated pull request queues, and secondary agent runtimes act only after validating the cryptographic bundle signature, base commit binding, and required pass verdicts.

## Deterministic computation graph (`compute.compose`)

The registry exposes `compute.compose`, a versioned execution graph whose variance nodes feed reconciliation nodes:

- **Topology validation**: Validates node identifiers, declared dependencies, metrics, currencies, and evaluation intervals prior to execution.
- **Preview and bounds**: Previews referenced variances during validation and refuses inputs exceeding declared operational thresholds.
- **Traceability**: Results preserve intermediates, topological execution order, and caller-supplied source references; unmatched keys remain explicitly unmatched.
- **Contract disclosure**: `compute.contract` returns machine-readable outer request schemas for financial reconciliation, variance calculation, and graph composition.

$$\Delta_{\text{reconciliation}} = \sum_{i \in \text{ledger}} v_i - \sum_{j \in \text{statement}} v_j = 0$$

Conservation invariants must balance to zero variance; non-zero differences fail verification closed and report unlinked items.

## Multimodal artifact ingestion and domain workflows

The verification runtime evaluates heterogeneous artifacts without widening token consumption or risking prompt pollution:

| Domain | Ingestion format | Deterministic check mechanism | Verification output |
|---|---|---|---|
| Engineering & CAD | Vector geometry, parameter tables, STEP/DXF | Bounded bounding box, collision envelope, coordinate invariants | Metric tolerances and geometric checks |
| Numerical & Physics | Mathematical models, formulas, matrix transforms | Unit conservation, dimensional analysis, stability bounds | Invariant proofs and convergence limits |
| Financial & Audit | Spreadsheets, transactional ledgers, reconciliation feeds | Decimal balance checks, double-entry equality, variance limits | Zero-discrepancy receipts |
| Document & Slides | Technical briefs, presentation decks, formatted briefs | Structural hierarchy, style token bounds, reading order | Layout audit metrics and format conformance |
| Medical & Laboratory | Clinical datasets, structured time-series, telemetry | Schema validity, range assertions, anomaly bounds | Bound assertion logs |
| Agent Visual State | Viewport renderings, layout audits at fixed widths (375 px) | Zero horizontal overflow, tap target minima, alt attributes | DOM layout audit JSON |

Visual progression over agent turns is verified by numerical layout audits and DOM geometry checks, avoiding lossy image re-encoding.

## Confidential information protection and authority tiers

Repository contents, external data, and generated agent programs remain untrusted until verified:

| Tier | Passport authority | Permitted scope | Boundary enforcement |
|---|---|---|---|
| Level 1 | Discovery Passport | Read-only MCP, catalog inspection, static guidance | No mutation authority; read-only responses |
| Level 2 | Workspace Passport | Repository hooks, local verify, reversible hygiene | In-repo changes only; out-of-tree writes refused |
| Level 3 | Enforcement Boundary | CI enforcement, sealed .ron execution, landing | Signed cryptographic receipts with zero unrun checks |

- **Level 1 (Discovery Passport)**: Read-only access to contracts, manifests, and documentation. No permission to mutate code or issue plan unlocks.
- **Level 2 (Workspace Passport)**: Local execution of verification gates and reversible hygiene fixes. Out-of-tree writes and unverified credential reads are refused.
- **Level 3 (Enforcement Boundary)**: Cryptographic signing, pull request gate enforcement, and branch landing. Requires verified check passes.

Token redaction, environment scrubbing, and proxy sanitization prevent secrets from escaping the sandbox during execution.

## Memory architecture and continuous learning

Recurring mistakes become automated enforcement guards:

1. **Intake and Ledger Recording**: Every failed gate registers its failure mode and input shape in the repository failure ledger.
2. **Defect Promotion**: A defect observed twice across sessions must receive a dedicated automated guard, proven by a planted defect test that fails when the guard is absent.
3. **Capacity-Aware Execution**: The scheduler prioritizes landing operations over speculative background work, throttling concurrent processes by observed machine capacity and idle cycles rather than static thread counts.
4. **Context Compaction**: Targeted repository routing delivers the obligations a file owes without whole-tree ingestion, reducing agent context requirements while preserving complete evidence.

## Ordered work

| Priority | Mechanism and next implementation | Evidence required to advance |
|---|---|---|
| Active | Finance, reconciliation, and graph share discoverable outer request schemas; operations retain detailed validation. | Nested cross-operation schemas, result schemas, and independent assumption review. |
| Active | The graph composes variance with reconciliation and validates declared dependencies and metadata. Extend only with explicitly typed edges. | Independent end-to-end examples, resource exhaustion, and partial-failure evidence; arbitrary code execution remains refused. |
| Next | Bind evidence and reuse to immutable identities: program, input, operator version, and relevant environment or external data identity. Refuse reuse when freshness is unverified. | Mutation cases for dirty files, changed inputs, and environment drift; compare reused results with clean recomputation. |
| Next | Capacity-aware execution slots: prioritize merge landings ahead of speculative discovery while respecting core budgets. | Measured queue latency, zero deadlocks, and verified slot release across concurrent agent sessions. |
| Measure | Compare retrieval, composition, and scheduling against unassisted baselines on representative tasks. Optimize only after collecting latency and failure metrics. | Repeatable baselines, held-out cases, uncertainty bounds, and regression thresholds. |

## Continuation

Next owner: extend the enforced contract to nested inputs and sealed outputs, then verify compatibility across multimodal artifact schemas. Maintain strict separation between open-source verification, local Harness execution, and hosted Mind services.
