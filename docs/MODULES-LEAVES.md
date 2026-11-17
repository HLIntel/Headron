# Module leaves

Part of [MODULES](MODULES.md). What each instrument proves is in [INSTRUMENTS](INSTRUMENTS.md).

<!-- BEGIN generated: module-leaves (python scripts/atlas.py index --write) -->
75 modules that at most one other module imports: 28 entry points that nothing imports, and single-use helpers. The shared ones and the diagram are in [MODULES.md](MODULES.md).

| module | what it is | used by | imports | tested by |
|---|---|---:|---|---|
| [agentbench](../scripts/agentbench.py) | Does an agent FINISH more real tasks with Headron? The arm every other bench here marks NOT RUN | 1 | agentpolicy, atlas, knowledge | [agentbench_test](../scripts/agentbench_test.py), [multimodel_bench_test](../scripts/multimodel_bench_test.py) |
| [agentvocab](../scripts/agentvocab.py) | The words a task contract may use for WHO does it, WITH WHAT, and IN WHICH LANGUAGES | 1 | headronlang | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [artifacts](../scripts/artifacts.py) | Artifact adapters: structured records and deterministic checks for office and archive files | 1 |  | [artifacts_test](../scripts/artifacts_test.py) |
| [atlas_cli](../scripts/atlas_cli.py) | Resolve WHICH atlas, then run the contract's CLI against it | 1 | atlas, headron_mcp | [bounds_test](../scripts/bounds_test.py), [cli_test](../scripts/cli_test.py) +1 |
| [cacheinv](../scripts/cacheinv.py) | Refuse cache artifacts in the repository index or unignored source tree | 1 |  | [edge_cases_test](../scripts/edge_cases_test.py) |
| [chatskill](../scripts/chatskill.py) | The claude.ai skill: Headron for a chat, with or without a sandbox, generated whole from atlas.yaml | 1 | agentpolicy, atlasgen, entryglance | [agent_test](../scripts/agent_test.py) |
| [codexbrief](../scripts/codexbrief.py) | Compact machine context for Codex and other runtimes | 1 | agentpolicy, dirscope |  |
| [consumerimpact](../scripts/consumerimpact.py) | Conservative Python import impact from a consumer's base commit | 1 |  | [consumer_test](../scripts/consumer_test.py) |
| [dateclaims](../scripts/dateclaims.py) | Calendar-claim validation, separate from CLI routing and contract orchestration | 1 |  |  |
| [decide_cli](../scripts/decide_cli.py) | CLI commands for the decision engine and pipeline | 1 | decide, pipeline, reflex |  |
| [delegate](../scripts/delegate.py) | The brief a delegated agent needs — `headron delegate [--task "..."]` | 1 |  | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [edges](../scripts/edges.py) | The test -> declaration edge: every planted case names the enforcer(s) its plant must trip | 1 | atlas, atlasgen, atlasinv, packmanifest, roster, safeedit, testgroups | [atlas_rules_test](../scripts/atlas_rules_test.py), [atlas_test](../scripts/atlas_test.py) +1 |
| [enforce](../scripts/enforce.py) | The enforcement rung at commit time, for ANY repository and ANY agent: refuse a change whose file… | 1 | agentpolicy, atomicfile, gateplace, gaterunner, localtools, verify | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) +3 |
| [failureledger](../scripts/failureledger.py) | The failure ledger's row-shape rules: the closed key set, and the `signature` regexes `headron… | 1 |  |  |
| [finance_capital](../scripts/finance_capital.py) | Periodic capital budgeting, with declared timing and no inferred cash flows | 1 |  |  |
| [finance_catalog](../scripts/finance_catalog.py) | Static instrument identifiers; no prices, trading venue or live ranking is implied | 1 |  | [microprogram_test](../scripts/microprogram_test.py) |
| [finance_knowledge](../scripts/finance_knowledge.py) | On-demand finance vocabulary; definitions are not project inputs | 1 |  |  |
| [formula](../scripts/formula.py) | Spreadsheet formulas for the data kit: parsed and evaluated, never executed | 1 |  | [formula_test](../scripts/formula_test.py) |
| [ghaudit](../scripts/ghaudit.py) | ghaudit — does the LIVE GitHub configuration match config/github-controls.json? | 1 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [githubjob](../scripts/githubjob.py) | The GitHub App's wire and queue shapes, as types only: nothing imports this at run time | 1 |  | [githubapp_test](../scripts/githubapp_test.py) |
| [githubreceipt](../scripts/githubreceipt.py) | Receipt loading, validation, and PR comment rendering for the Headron GitHub App | 1 | githubapp, receipt, receiptsign |  |
| [hostshape](../scripts/hostshape.py) | Shapes that break on the operator's HOST, checked from the records the host hands in | 1 |  | [schedtargets_test](../scripts/schedtargets_test.py) |
| [i18n](../scripts/i18n.py) | Localized entry points with canonical, generated command references | 1 |  |  |
| [identity](../scripts/identity.py) | Who owns this tree, compared against the declaration — and the rename, as one operation | 1 |  | [identity_test](../scripts/identity_test.py) |
| [intake](../scripts/intake.py) | A user's prompt, digested into a task — or into the questions that make it one | 1 | agentpolicy, codexbrief, commands, knowledge | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [isolation](../scripts/isolation.py) | Capability-enforced worker isolation for task and gate execution | 1 |  | [isolation_test](../scripts/isolation_test.py) |
| [langbar](../scripts/langbar.py) | What the language bar will say, computed from the tree rather than predicted | 1 | contextcost |  |
| [leaks](../scripts/leaks.py) | The public-repository rule, ENFORCED: no private path, address, internal host or runtime store is… | 1 | importgraph | [agents_test](../scripts/agents_test.py), [cli_test](../scripts/cli_test.py) +2 |
| [mind_verifier](../scripts/mind_verifier.py) | Optional entitlement verification for customer-controlled Mind execution, and the Action's key… | 1 |  | [mind_action_test](../scripts/mind_action_test.py) |
| [model](../scripts/model.py) | `headron model` — which rung answers each typed judgment, read from the attached student bundle | 1 | modelpack | [model_test](../scripts/model_test.py) |
| [modelpack](../scripts/modelpack.py) | modelpack — the student rung's loader: read a verified micro-pack bundle and answer from it | 1 |  | [model_test](../scripts/model_test.py) |
| [nativetools](../scripts/nativetools.py) | native_agent_tools_are_kept: Headron is ADDED to an agent runtime's layer and never removes a tool… | 1 |  | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [orphans](../scripts/orphans.py) | Dead harness code: a top-level function or class that nothing in the tree names but its own… | 1 | importgraph | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [parsegate](../scripts/parsegate.py) | Every tracked artifact parses: the first thing the contract asks, since nothing after it means… | 1 | headronlang |  |
| [pipeline](../scripts/pipeline.py) | State-to-action pipeline — finite state machine: INGEST → CLASSIFY → VERIFY → EXIT | 1 | decide, reflex | [pipeline_test](../scripts/pipeline_test.py) |
| [plantcheck](../scripts/plantcheck.py) | plants_can_still_apply: every mutation anchor in the planted suites still matches the file it aims… | 1 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [privacy_guard](../scripts/privacy_guard.py) | Refuse personal data and secrets before they reach a commit, a push, or the shared history | 1 |  | [privacy_guard_test](../scripts/privacy_guard_test.py) |
| [processpolicy](../scripts/processpolicy.py) | Declared workflow records and their stopping conditions | 1 | agentpolicy |  |
| [ronbundle](../scripts/ronbundle.py) | A `.ron` bundle: one task's contract, receipts and evidence as a directory that verifies from its… | 1 | atomicfile, obligations, receipt, receiptsign | [microprogram_test](../scripts/microprogram_test.py), [receiptsign_test](../scripts/receiptsign_test.py) |
| [scoreboard](../scripts/scoreboard.py) | What the benchmarks measure, as a floor that only rises: one row per metric, simple enough to act on | 1 |  |  |
| [shellsplit](../scripts/shellsplit.py) | The shell-string helpers shell_verdict reads: top-level statements, pipeline stages, heredoc bodies | 1 |  |  |
| [taskbench](../scripts/taskbench.py) | Does Headron make a model better at work OTHER than routing? Blind against with-Headron, per task… | 1 | abtest, agentpolicy, providers |  |
| [textguard](../scripts/textguard.py) | Characters in tracked text that a reader cannot see, or cannot tell apart | 1 |  |  |
| [treeformat](../scripts/treeformat.py) | Working-tree formatting and blame-history checks | 1 | gitobject |  |
| [verifyinputs](../scripts/verifyinputs.py) | Content identities for verification evidence | 1 |  |  |
| [workflowbench](../scripts/workflowbench.py) | Does Headron change what agents DO — alone, and when one hands work to another? Measured, per model | 1 | abtest, agentpolicy, dirscope | [atlas_test](../scripts/atlas_test.py) |
| [yamlshape](../scripts/yamlshape.py) | yaml_prose_is_quoted: prose inside a YAML flow collection is quoted, so a comma cannot silently… | 1 |  | [atlas_rules_test](../scripts/atlas_rules_test.py), [edge_cases_test](../scripts/edge_cases_test.py) |
| [astshape](../scripts/astshape.py) | astshape — structural duplicates and code blobs, by AST rather than by text | 0 |  |  |
| [atlasci](../scripts/atlasci.py) | What a consuming repository's pull request requires, resolved against a pinned atlas | 0 | agentpolicy |  |
| [bench](../scripts/bench.py) | Does using the atlas actually help? Measured where it can be, and REFUSED where it cannot | 0 | agentpolicy | [atlas_test](../scripts/atlas_test.py) |
| [brainstorm](../scripts/brainstorm.py) | brainstorm — a strategic brainstorm as a record a program can refuse: diverge, pre-mortem,… | 0 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [cadence](../scripts/cadence.py) | The time-boxed session, declared once and printed as a clock — `headron cadence [--minutes N]` | 0 |  | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [ci](../scripts/ci.py) | `headron ci`: run THIS checkout's CI, the jobs its own scripts/cipipeline.py declares | 0 |  | [cilocal_test](../scripts/cilocal_test.py) |
| [claude_hook](../scripts/claude_hook.py) | Claude Code PreToolUse adapter: refuses the pushes and bypasses the repository forbids, before they… | 0 | boundedinput, gitobject | [claude_hook_test](../scripts/claude_hook_test.py) |
| [datakit](../scripts/datakit.py) | Data kit: read tables from data files, check them against a schema, trace a report's numbers | 0 | artifacts, formula | [datakit_test](../scripts/datakit_test.py) |
| [economic_benchmark](../scripts/economic_benchmark.py) | Economic benchmark: Headron-assisted vs unassisted agents, from the recorded runs only | 0 |  | [economic_benchmark_test](../scripts/economic_benchmark_test.py) |
| [freshness](../scripts/freshness.py) | Which parts of this tree have not been re-examined lately — measured in CONTRACT VERSIONS | 0 |  | [handoff_test](../scripts/handoff_test.py) |
| [handoff](../scripts/handoff.py) | A bounded, artifact-specific handoff — route evidence instead of a repository dump | 0 | agentpolicy, atlas | [handoff_test](../scripts/handoff_test.py) |
| [headron_edit](../scripts/headron_edit.py) | The MCP route that may EDIT — separate, opt-in, and bounded by the task contract it is started with | 0 | agentaudit, agentpolicy, headron_mcp, safeedit | [atlas_guards_test](../scripts/atlas_guards_test.py), [edit_version_test](../scripts/edit_version_test.py) |
| [installcheck](../scripts/installcheck.py) | Run the install command the documents give, in a clean home, and judge `headron doctor` by exit code | 0 |  | [cli_test](../scripts/cli_test.py) |
| [judge](../scripts/judge.py) | `headron judge` — a small decision asked as a closed question, acted on only above a declared bar | 0 | boundedinput, knowledge, model | [judge_test](../scripts/judge_test.py), [model_test](../scripts/model_test.py) |
| [links](../scripts/links.py) | `headron links`: where this release is, and what each companion reads from it | 0 | commands |  |
| [mcpsize](../scripts/mcpsize.py) | Measure an MCP `tools/list` dump against the declared per-server token band | 0 | contextcost |  |
| [mdshape](../scripts/mdshape.py) | mdshape — every Markdown file has a class, and each class has a rule: bounded, preserved, or… | 0 |  | [atlas_rules_test](../scripts/atlas_rules_test.py), [cli_test](../scripts/cli_test.py) |
| [multimodel_bench](../scripts/multimodel_bench.py) | Multi-model cross-evaluation benchmark: Headron lift, tokens, and multi-model collaboration | 0 | abtest, agentbench, providers, resilience, taskbench | [multimodel_bench_test](../scripts/multimodel_bench_test.py) |
| [packprobe](../scripts/packprobe.py) | packprobe — how many of each language pack's DECLARED commands resolve on this machine | 0 | packmanifest |  |
| [pointers](../scripts/pointers.py) | The pointer table: every name in atlas.yaml that points at something else, in one place, read by… | 0 | knowledge, packmanifest | [pointers_test](../scripts/pointers_test.py) |
| [propose](../scripts/propose.py) | Propose: a loop that reads what Headron believes, drafts the revision, and never lands it | 0 | atomicfile, claims | [propose_test](../scripts/propose_test.py) |
| [sandboxgen](../scripts/sandboxgen.py) | Generate the host sandbox a task contract needs, from config/agent-sandbox.json | 0 | headronlang | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [schedtargets](../scripts/schedtargets.py) | Every ACTIVE scheduled job's target must exist on THIS host — `headron schedtargets [--root DIR]… | 0 |  | [schedtargets_test](../scripts/schedtargets_test.py) |
| [seats](../scripts/seats.py) | Attach declared agent, model, chat, and plugin seats on this machine | 0 | atomicfile |  |
| [staleness](../scripts/staleness.py) | What was edited longest ago, and which worktrees are hung — computed from git, never typed | 0 |  | [atlas_test](../scripts/atlas_test.py), [vanish_test](../scripts/vanish_test.py) |
| [taskimage](../scripts/taskimage.py) | Task image: one task's contract, gate graph, results, obligations and receipt, kept as a git commit… | 0 | agentpolicy, agentrun, crosscache, gitobject, headronlang, obligations, privacy_guard | [taskimage_portable_test](../scripts/taskimage_portable_test.py), [taskimage_test](../scripts/taskimage_test.py) |
| [workflow_runner](../scripts/workflow_runner.py) | One task through Connect -> Context -> Gates -> Receipt, with every declared gate's verdict as… | 0 | agentpolicy, agentrun, atlas, obligations, receipt, runtime, verify | [workflow_runner_test](../scripts/workflow_runner_test.py) |
| [worktree](../scripts/worktree.py) | Worktree-based agent isolation — each session gets its own git worktree | 0 |  |  |
<!-- END generated: module-leaves -->
