# Modules

[HEADRON](HEADRON.md) · [Proofs](INSTRUMENTS.md).

<!-- BEGIN generated: module-map (python scripts/atlas.py index --write) -->
149 modules and 466 imports between them, read from the source; 80 test modules are left out of the rows. In the diagram an arrow is an import and the number is how many modules use that hub. `atlascore` is left out of the diagram and the imports column, because 104 modules use it. These 71 rows are the modules at least 2 others use; the other 78, entry points and single-use helpers, are in [MODULES-LEAVES.md](MODULES-LEAVES.md).

```mermaid
flowchart LR
  m_agentpolicy["agentpolicy (30)"]
  m_atlas["atlas (10)"]
  m_atomicfile["atomicfile (11)"]
  m_commands["commands (8)"]
  m_contextcost["contextcost (8)"]
  m_dirscope["dirscope (8)"]
  m_headronlang["headronlang (8)"]
  m_knowledge["knowledge (15)"]
  m_receipt["receipt (8)"]
  m_safeedit["safeedit (9)"]
  m_verify["verify (10)"]
  m_agentpolicy --> m_dirscope
  m_agentpolicy --> m_headronlang
  m_atlas --> m_agentpolicy
  m_atlas --> m_commands
  m_atlas --> m_contextcost
  m_atlas --> m_dirscope
  m_atlas --> m_headronlang
  m_atlas --> m_knowledge
  m_atlas --> m_safeedit
  m_atlas --> m_verify
  m_dirscope --> m_knowledge
  m_headronlang --> m_agentpolicy
  m_headronlang --> m_dirscope
  m_headronlang --> m_knowledge
  m_receipt --> m_safeedit
  m_verify --> m_agentpolicy
  m_verify --> m_atlas
  m_verify --> m_receipt
  m_verify --> m_safeedit
```

| module | what it is | used by | imports | tested by |
|---|---|---:|---|---|
| [atlascore](../scripts/atlascore.py) | Atlas primitives: the declared rosters, the… | 104 |  | [agent_test](../scripts/agent_test.py), [agentbench_test](../scripts/agentbench_test.py) +16 |
| [agentpolicy](../scripts/agentpolicy.py) | The agent execution policy: six verdicts,… | 30 | agenteffects, agentvocab, dirscope, headronlang, packmanifest, processpolicy, shellsplit | [agent_properties_test](../scripts/agent_properties_test.py), [agent_test](../scripts/agent_test.py) +9 |
| [knowledge](../scripts/knowledge.py) | Where a fact may live, how it is retrieved,… | 15 |  | [atlas_landing_test](../scripts/atlas_landing_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [atomicfile](../scripts/atomicfile.py) | Replace one file whole: a reader sees the… | 11 |  | [atomicfile_test](../scripts/atomicfile_test.py) |
| [atlas](../scripts/atlas.py) | Atlas router + repository contract | 10 | agentpolicy, agreement, atlasgen, atlasindex, atlasinv, branchstate, cidrift, commands, consumergates, contextcost, dateclaims, decide, decide_cli, declcheck, dirscope, doctor, gateplace, headronlang, identity, knowledge, knowledgecli, linkcheck, obligations, onboard, packmanifest, parsegate, roster, safeedit, toolpins, verify | [agents_test](../scripts/agents_test.py), [atlas_guards_test](../scripts/atlas_guards_test.py) +7 |
| [verify](../scripts/verify.py) | Run the declared checks and return a verdict… | 10 | agentpolicy, agents, atlas, branchstate, edges, impact, localtools, receipt, resilience, runtime, safeedit, upstream, verifyinputs | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_landing_test](../scripts/atlas_landing_test.py) +10 |
| [safeedit](../scripts/safeedit.py) | Edits that cannot fail silently: an anchor… | 9 |  | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_landing_test](../scripts/atlas_landing_test.py) +3 |
| [commands](../scripts/commands.py) | What Headron answers, in one place: the… | 8 |  | [cli_test](../scripts/cli_test.py), [clihelp_test](../scripts/clihelp_test.py) +1 |
| [contextcost](../scripts/contextcost.py) | What this repository HANDS OVER before it is… | 8 | importgraph, intake | [deps_test](../scripts/deps_test.py) |
| [dirscope](../scripts/dirscope.py) | Directory scopes: what a PLACE in this… | 8 | knowledge | [atlas_rules_test](../scripts/atlas_rules_test.py), [cli_test](../scripts/cli_test.py) +1 |
| [headronlang](../scripts/headronlang.py) | The surface notation: a `.headron` program… | 8 | agenteffects, agentpolicy, dirscope, knowledge | [agent_test](../scripts/agent_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) +1 |
| [receipt](../scripts/receipt.py) | Headron receipt v1: one verify run as a… | 8 | receiptsign, safeedit | [computation_receipt_test](../scripts/computation_receipt_test.py), [compute_compose_test](../scripts/compute_compose_test.py) +6 |
| [importgraph](../scripts/importgraph.py) | One reading of what a Python module imports,… | 7 |  | [importgraph_test](../scripts/importgraph_test.py) |
| [packmanifest](../scripts/packmanifest.py) | The language tool manifest contract — ONE… | 7 | agentpolicy | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_test](../scripts/atlas_test.py) +1 |
| [obligations](../scripts/obligations.py) | Task Obligation Ledger: a task's… | 6 | agentpolicy, atlas, headronlang, verify | [microprogram_test](../scripts/microprogram_test.py), [receiptsign_test](../scripts/receiptsign_test.py) +2 |
| [resilience](../scripts/resilience.py) | Retry what can succeed, refuse what cannot,… | 6 |  | [agent_test](../scripts/agent_test.py), [atlas_test](../scripts/atlas_test.py) +5 |
| [runtime](../scripts/runtime.py) | Which agent runtime produced a change —… | 6 |  | [runtime_test](../scripts/runtime_test.py) |
| [abtest](../scripts/abtest.py) | Does the atlas actually help a model? Three… | 5 | agentpolicy, atlasinv, contextcost, providers, resilience | [agent_test](../scripts/agent_test.py), [bounds_test](../scripts/bounds_test.py) +1 |
| [branchstate](../scripts/branchstate.py) | Unpushed work, bounded by what actually… | 5 | cilocal, consumergates, doctor, gaterunner, ghaudit, verify | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_landing_test](../scripts/atlas_landing_test.py) +7 |
| [decide](../scripts/decide.py) | Compiled decision table engine — the System… | 5 |  | [decide_test](../scripts/decide_test.py), [reflex_test](../scripts/reflex_test.py) |
| [port](../scripts/port.py) | port — plug any agent into everything… | 5 | agreement, atlas, commands, dirscope, knowledge, localtools, sweep, upstream | [atlas_rules_test](../scripts/atlas_rules_test.py), [sweep_test](../scripts/sweep_test.py) +1 |
| [agentaudit](../scripts/agentaudit.py) | The audit stream: a hash chain, not a log | 4 |  | [agent_properties_test](../scripts/agent_properties_test.py), [agent_test](../scripts/agent_test.py) +2 |
| [agents](../scripts/agents.py) | Which agent sessions are live on this… | 4 | agentaudit, atomicfile, cilocal, runtime | [agents_test](../scripts/agents_test.py), [atlas_landing_test](../scripts/atlas_landing_test.py) +2 |
| [agreement](../scripts/agreement.py) | The agreement graph: which file implements… | 4 | atlasinv, commands | [atlas_landing_test](../scripts/atlas_landing_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) +1 |
| [atlasgen](../scripts/atlasgen.py) | Every document section and file GENERATED… | 4 | abtest, chatskill, commands, contextcost, dirscope, entryglance, exrun, i18n, knowledgecli, packmanifest, textguard | [atlas_test](../scripts/atlas_test.py), [edge_cases_test](../scripts/edge_cases_test.py) +2 |
| [atlasinv](../scripts/atlasinv.py) | The hard invariants: one function per… | 4 | agentpolicy, atlasgen, cacheinv, callshape, cidrift, contextcost, declcheck, failureledger, knowledge, langbar, leaks, nativetools, orphans, packmanifest, plantcheck, roster, scoreboard, testgroups, treeformat, yamlshape | [atlas_test](../scripts/atlas_test.py), [edge_cases_test](../scripts/edge_cases_test.py) +2 |
| [calculation](../scripts/calculation.py) | Shared result and refusal contract for… | 4 | computation_contract, effects, microprogram, receipt | [computation_receipt_test](../scripts/computation_receipt_test.py) |
| [graph](../scripts/graph.py) | Knowledge graph module — pointers, links,… | 4 | claims, exrun | [decide_test](../scripts/decide_test.py), [microprogram_test](../scripts/microprogram_test.py) |
| [localtools](../scripts/localtools.py) | The tool a project installed for itself,… | 4 |  | [localtools_test](../scripts/localtools_test.py) |
| [microprogram](../scripts/microprogram.py) | The one microprogram contract: a named,… | 4 | claims, computation_contract, compute_compose, domain_reconcile, effects, finance, graph, mind, obligations, receipt, ronbundle | [cilocal_test](../scripts/cilocal_test.py), [computation_receipt_test](../scripts/computation_receipt_test.py) +3 |
| [receiptsign](../scripts/receiptsign.py) | Who wrote a receipt: a detached SSH… | 4 | receipt | [githubapp_test](../scripts/githubapp_test.py), [receiptsign_test](../scripts/receiptsign_test.py) |
| [agenteffects](../scripts/agenteffects.py) | Effects: what a task may DO, as a kind… | 3 | agentpolicy | [agent_test](../scripts/agent_test.py) |
| [boundedinput](../scripts/boundedinput.py) | Bounded UTF-8 stdin for hooks and local… | 3 |  | [readiness_test](../scripts/readiness_test.py) |
| [cidrift](../scripts/cidrift.py) | Drift guard: every script CI runs is a… | 3 | cipipeline | [cilocal_test](../scripts/cilocal_test.py) |
| [cipipeline](../scripts/cipipeline.py) | Headron's CI, declared in Python: every job,… | 3 | micrograph | [cilocal_test](../scripts/cilocal_test.py) |
| [claims](../scripts/claims.py) | Claims: what Headron believes, the evidence… | 3 |  | [claims_test](../scripts/claims_test.py) |
| [consumergates](../scripts/consumergates.py) | Consumer gate discovery, shared by landing… | 3 | consumerimpact, verify | [consumer_test](../scripts/consumer_test.py) |
| [gaterunner](../scripts/gaterunner.py) | Bounded process capture shared by… | 3 |  | [gaterunner_test](../scripts/gaterunner_test.py), [readiness_test](../scripts/readiness_test.py) |
| [gitobject](../scripts/gitobject.py) | Git's object identity, computed in this… | 3 |  | [gitobject_test](../scripts/gitobject_test.py) |
| [mind](../scripts/mind.py) | Headron Mind API — unified orchestration… | 3 | adaptive, agentpolicy, atlasindex, decide, graph, knowledge, microprogram, mind_diagnostics, port, receipt, reflex, safeedit, slot, sweep, verify | [mcp_test](../scripts/mcp_test.py), [microprogram_test](../scripts/microprogram_test.py) +1 |
| [providers](../scripts/providers.py) | Where a measurement may send a prompt:… | 3 | atomicfile, resilience | [agent_test](../scripts/agent_test.py), [multimodel_bench_test](../scripts/multimodel_bench_test.py) |
| [reflex](../scripts/reflex.py) | Command classification primitives —… | 3 | branchstate, callshape, decide, importgraph, port | [reflex_test](../scripts/reflex_test.py) |
| [roster](../scripts/roster.py) | instrument_roster: which scripts are… | 3 | cidrift, cipipeline, dirscope, importgraph | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [sweep](../scripts/sweep.py) | Fast semantic sweep: repo-wide… | 3 | graph, port | [sweep_test](../scripts/sweep_test.py) |
| [testgroups](../scripts/testgroups.py) | Run independent planted groups without… | 3 | impact | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_landing_test](../scripts/atlas_landing_test.py) +9 |
| [adaptive](../scripts/adaptive.py) | Deterministic second-stage process selection… | 2 | mind, mind_diagnostics | [adaptive_scheduling_test](../scripts/adaptive_scheduling_test.py) |
| [agentrun](../scripts/agentrun.py) | The reference runner: the one caller in this… | 2 | agentaudit, agenteffects, agentpolicy, crosscache, headronlang, isolation, knowledge, obligations, runtime | [agent_test](../scripts/agent_test.py), [taskimage_test](../scripts/taskimage_test.py) |
| [atlasindex](../scripts/atlasindex.py) | A retrieval index that obeys the policy this… | 2 | atomicfile, graph, microcode, port, sweep | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_test](../scripts/atlas_test.py) +1 |
| [callshape](../scripts/callshape.py) | forbidden_calls_are_refused: "no module… | 2 | agentpolicy | [atlas_rules_test](../scripts/atlas_rules_test.py), [atomicfile_test](../scripts/atomicfile_test.py) +1 |
| [cilocal](../scripts/cilocal.py) | `headron ci`: run the jobs… | 2 | agents, cipipeline, gaterunner, micrograph, microprogram, slot | [atlas_landing_test](../scripts/atlas_landing_test.py), [cilocal_test](../scripts/cilocal_test.py) +1 |
| [computation_contract](../scripts/computation_contract.py) | Machine-readable and enforced outer… | 2 | calculation, compute_compose | [computation_contract_test](../scripts/computation_contract_test.py) |
| [compute_compose](../scripts/compute_compose.py) | Bounded computation graph for variance… | 2 | calculation, domain_reconcile, finance | [compute_compose_test](../scripts/compute_compose_test.py) |
| [crosscache](../scripts/crosscache.py) | Cross-session execution cache and task DAG… | 2 | agentpolicy, atomicfile, safeedit | [crosscache_test](../scripts/crosscache_test.py) |
| [declcheck](../scripts/declcheck.py) | declarations_are_read: a block in atlas.yaml… | 2 | abtest, agentpolicy, commands, delegate, knowledge, workflowbench | [agent_test](../scripts/agent_test.py), [timeout_test](../scripts/timeout_test.py) +2 |
| [doctor](../scripts/doctor.py) | doctor — can THIS machine run each… | 2 | agentpolicy, agreement, atlas_cli, githubapp | [atlas_test](../scripts/atlas_test.py), [bounds_test](../scripts/bounds_test.py) |
| [domain_reconcile](../scripts/domain_reconcile.py) | Compare caller-supplied records by declared… | 2 | calculation |  |
| [effects](../scripts/effects.py) | What a microprogram may do besides compute:… | 2 |  | [effects_test](../scripts/effects_test.py), [microcache_test](../scripts/microcache_test.py) |
| [entryglance](../scripts/entryglance.py) | Shared first-glance facts for entry pages… | 2 | onboard |  |
| [exrun](../scripts/exrun.py) | exrun — run every example this machine can,… | 2 | atomicfile, contextcost, resilience | [exrun_test](../scripts/exrun_test.py) |
| [finance](../scripts/finance.py) | On-demand, read-only financial equations… | 2 | calculation, finance_capital, finance_catalog, finance_knowledge |  |
| [gateplace](../scripts/gateplace.py) | Where one gate runs for one file, and… | 2 |  | [atlas_gate_adoption_test](../scripts/atlas_gate_adoption_test.py), [atlas_landing_test](../scripts/atlas_landing_test.py) |
| [githubapp](../scripts/githubapp.py) | The Headron GitHub App, one module: every… | 2 | agentpolicy, atomicfile, branchstate, githubjob, githubreceipt, knowledge, runtime | [githubapp_test](../scripts/githubapp_test.py), [runtime_test](../scripts/runtime_test.py) |
| [headron_mcp](../scripts/headron_mcp.py) | Headron as an MCP server: the same commands… | 2 | agents, atlas, commands, mind_verifier | [agents_test](../scripts/agents_test.py), [atlas_guards_test](../scripts/atlas_guards_test.py) +3 |
| [impact](../scripts/impact.py) | The runtime test-impact map: which… | 2 | atomicfile, importgraph, safeedit, testgroups, verify | [atlas_rules_test](../scripts/atlas_rules_test.py), [impact_test](../scripts/impact_test.py) |
| [knowledgecli](../scripts/knowledgecli.py) | Knowledge commands and hooks | 2 | agentaudit, agentpolicy, agents, agreement, atlas, boundedinput, contextcost, hostshape, knowledge, port, runtime, safeedit, verify | [agents_test](../scripts/agents_test.py), [facts_test](../scripts/facts_test.py) +2 |
| [micrograph](../scripts/micrograph.py) | A DAG of microprogram steps: run each node… | 2 | microprogram | [cilocal_test](../scripts/cilocal_test.py) |
| [mind_diagnostics](../scripts/mind_diagnostics.py) | Headron Mind API Diagnostics & Recovery —… | 2 | adaptive, knowledge, mind |  |
| [onboard](../scripts/onboard.py) | `headron init`: the first five minutes in a… | 2 | branchstate, consumergates, enforce, localtools, verify |  |
| [slot](../scripts/slot.py) | A few heavy suites per MACHINE, across every… | 2 | resilience | [slot_test](../scripts/slot_test.py) |
| [treeformat](../scripts/treeformat.py) | Working-tree formatting and blame-history… | 2 | gitobject | [cli_test](../scripts/cli_test.py) |
| [upstream](../scripts/upstream.py) | THE UPSTREAM COUNT (3.53.0): commits on the… | 2 |  | [upstream_test](../scripts/upstream_test.py) |
<!-- END generated: module-map -->
