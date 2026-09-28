# Language Stack Specification

Every language guide follows a common reasoning schema so agents can switch languages without changing their operating model.

Required:
1. purpose
2. when to use
3. when not to use
4. guarantees/model
5. stack/toolchain
6. project/package/workspace
7. state/mutation
8. concurrency
9. interoperability/FFI
10. performance/profiling
11. security/hygiene
12. cloud/deployment shape
13. uptime/reliability/observability
14. Redis/Upstash/cache/data stores
15. database/schema/transaction practice
16. endpoint/API/webhook testing
17. mutation/property/fuzz/regression testing
18. bug and breakage prevention
19. blob/module-growth prevention
20. common mistakes
21. streamlining
22. learning direction
23. avoid
24. AI coding directive
25. verification
26. worktree/parallel development
27. official sources
28. VS Code + MCP integration

Shared production-operations details live in [wiki/LANGUAGE-OPERATIONS.md](../wiki/LANGUAGE-OPERATIONS.md), while each language guide retains decisions that materially affect runtime, data, endpoints, testing, or failure behavior.

The final section must name native editor/LSP/debugger/test tooling, MCP recommendation level, applicable shared profiles, duplication to avoid, external services/keys, and bounded tool behavior.

Do not invent dedicated MCPs. When none is credible, use native tooling plus the shared GitHub/documentation/semantic layers where appropriate.

## What each language PROVES, and whether this atlas took it

`language_selection` answers which language for which need. This answers the other question: what
MECHANISM a language demonstrated well enough that an agent contract should carry the same shape.
The mechanism is harvested, never the syntax — a notation that borrowed Go's braces and not Go's
context would have taken the part that does not matter.

Every row is `harvested` or `refused`. There is no third status: a mechanism listed as someday-work
is an aspiration, and an unshipped arm reads as covered. A harvest must resolve to a callable, an
atlas key or a path; a refusal must carry its reason, because a no with no reason is re-proposed by
the next reader.

<!-- BEGIN generated: mechanism-harvest (python scripts/atlas.py index --write) -->
| mechanism | from | status | where it lives, or why not |
|---|---|---|---|
| `a_declared_floor_refuses_forward` | `go` | harvested | `agentvocab.floor_errors` |
| `a_run_may_not_amend_its_own_declaration` | `go` | harvested | `agentpolicy.contract_errors` |
| `the_generated_marker_lives_in_the_artifact` | `go` | harvested | `atlasgen.generated_file_errors` |
| `visibility_from_path_position` | `go` | refused | nothing in this tree is laid out that way, so it would be a rule with zero instances — an arm built, measured and never exercised, which is the shape refused everywhere else here. The enumerated directory_scopes never-lists are short and each names a file that exists; when a subtree earns the pattern this becomes worth revisiting |
| `errors_are_values` | `go` | harvested | `agentpolicy.Verdict` |
| `context_deadline_propagation` | `go` | harvested | `agenteffects.delegation_errors` |
| `deferred_cleanup` | `go` | refused | the runner resolves gate argv FROM the atlas and executes nothing else, so a general defer would need a contract to carry full argv and command_name refuses that on purpose; the one case measured here, a killed run leaving a plant, is closed by safeedit's journal and `--restore` |
| `effects_in_the_type` | `haskell` | harvested | `agenteffects.contract_effect_errors` |
| `proof_before_acceptance` | `lean4` | harvested | `atlas.yaml/verification_policy` |
| `exclusive_ownership` | `rust` | harvested | `atlas_test.suite_lock` |
| `scoped_acquire_release` | `python` | harvested | `atlas_test.mutated` |
| `bounded_restart` | `elixir` | harvested | `agentpolicy.effective_budgets` |
| `structural_conformance` | `typescript` | harvested | `packmanifest.validate` |
| `declarative_query_over_a_schema` | `sql` | harvested | `atlas.route_record` |
| `exit_code_is_the_verdict` | `bash` | harvested | `scripts/verify.py` |
| `no_hidden_allocation` | `zig` | harvested | `agentpolicy.budget_verdict` |
| `exhaustive_match` | `ocaml` | harvested | `roster.instrument_roster_errors` |
| `a_measurement_collapses_state` | `quantum/qsharp` | harvested | `atlas.yaml/agent_failure_modes` |
| `undefined_behaviour_as_optimisation_licence` | `c` | refused | a parser or a policy that resolves an ambiguous input is worse than one that errors, because the ambiguity leaves no trace and the wrong answer is indistinguishable from the right one; `none` is a real answer here and refusing is the declared discipline |
| `isolate_per_request` | `cloudflare` | refused | this repository runs no service, and the isolation an agent run needs is decided by the HOST — the sandbox rows agentrun prints UNOBSERVED are exactly that boundary, and claiming it here would be claiming a control nothing in this tree observes |
<!-- END generated: mechanism-harvest -->
