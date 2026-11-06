# Module leaves

Part of [MODULES](MODULES.md). What each instrument proves is in [INSTRUMENTS](INSTRUMENTS.md).

<!-- BEGIN generated: module-leaves (python scripts/atlas.py index --write) -->
64 modules that at most one other module imports: 26 entry points that nothing imports, and single-use helpers. The shared ones and the diagram are in [MODULES.md](MODULES.md).

| module | what it is | used by | imports | tested by |
|---|---|---:|---|---|
| [agentvocab](../scripts/agentvocab.py) | The words a task contract may use for WHO does it, WITH WHAT, and IN WHICH LANGUAGES | 1 | headronlang | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [artifacts](../scripts/artifacts.py) | Artifact adapters: structured records and deterministic checks for office and archive files | 1 |  | [artifacts_test](../scripts/artifacts_test.py) |
| [atlas_cli](../scripts/atlas_cli.py) | Resolve WHICH atlas, then run the contract's CLI against it | 1 | atlas, headron_mcp | [bounds_test](../scripts/bounds_test.py), [cli_test](../scripts/cli_test.py) +1 |
| [cacheinv](../scripts/cacheinv.py) | Refuse cache artifacts in the repository index or unignored source tree | 1 |  | [edge_cases_test](../scripts/edge_cases_test.py) |
| [callshape](../scripts/callshape.py) | forbidden_calls_are_refused: "no module outside X may call Y" is a declared ROW, not a function | 1 | agentpolicy | [atlas_rules_test](../scripts/atlas_rules_test.py), [atomicfile_test](../scripts/atomicfile_test.py) +1 |
| [chatskill](../scripts/chatskill.py) | The claude.ai skill: Headron for a chat, with or without a sandbox, generated whole from atlas.yaml | 1 | agentpolicy, atlasgen, entryglance | [agent_test](../scripts/agent_test.py) |
| [cilocal](../scripts/cilocal.py) | Replay atlas-ci.yml's contract jobs on this machine, translating the GitHub expressions they use | 1 | resilience, slot | [atlas_landing_test](../scripts/atlas_landing_test.py), [cilocal_test](../scripts/cilocal_test.py) |
| [codexbrief](../scripts/codexbrief.py) | Compact machine context for Codex and other runtimes | 1 | agentpolicy, dirscope |  |
| [dateclaims](../scripts/dateclaims.py) | Calendar-claim validation, separate from CLI routing and contract orchestration | 1 |  |  |
| [decide_cli](../scripts/decide_cli.py) | CLI commands for the decision engine and pipeline | 1 | decide, pipeline, reflex |  |
| [delegate](../scripts/delegate.py) | The brief a delegated agent needs — `headron delegate [--task "..."]` | 1 |  | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [edges](../scripts/edges.py) | The test -> declaration edge: every planted case names the enforcer(s) its plant must trip | 1 | atlas, atlasgen, atlasinv, packmanifest, roster, safeedit, testgroups | [atlas_rules_test](../scripts/atlas_rules_test.py), [atlas_test](../scripts/atlas_test.py) +1 |
| [enforce](../scripts/enforce.py) | The enforcement rung at commit time, for ANY repository and ANY agent: refuse a change whose file fails its… | 1 | agentpolicy, atomicfile, gaterunner, localtools, verify | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) +2 |
| [exrun](../scripts/exrun.py) | exrun — run every example this machine can, and say why it skipped the rest | 1 | atomicfile, contextcost, resilience | [exrun_test](../scripts/exrun_test.py) |
| [failureledger](../scripts/failureledger.py) | The failure ledger's row-shape rules: the closed key set, and the `signature` regexes `headron failures… | 1 |  |  |
| [ghaudit](../scripts/ghaudit.py) | ghaudit — does the LIVE GitHub configuration match config/github-controls.json? | 1 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [githubapp](../scripts/githubapp.py) | The Headron GitHub App, one module: every pushed head gets a real "Headron verify" check run | 1 | agentpolicy, atomicfile, branchstate, githubjob, knowledge, runtime | [githubapp_test](../scripts/githubapp_test.py), [runtime_test](../scripts/runtime_test.py) |
| [githubjob](../scripts/githubjob.py) | The GitHub App's wire and queue shapes, as types only: nothing imports this at run time | 1 |  | [githubapp_test](../scripts/githubapp_test.py) |
| [hostshape](../scripts/hostshape.py) | Shapes that break on the operator's HOST, checked from the records the host hands in | 1 |  | [schedtargets_test](../scripts/schedtargets_test.py) |
| [identity](../scripts/identity.py) | Who owns this tree, compared against the declaration — and the rename, as one operation | 1 |  | [identity_test](../scripts/identity_test.py) |
| [intake](../scripts/intake.py) | A user's prompt, digested into a task — or into the questions that make it one | 1 | agentpolicy, codexbrief, commands, knowledge | [atlas_guards_test](../scripts/atlas_guards_test.py), [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [langbar](../scripts/langbar.py) | What the language bar will say, computed from the tree rather than predicted | 1 | contextcost |  |
| [leaks](../scripts/leaks.py) | The public-repository rule, ENFORCED: no private path, address, internal host or runtime store is tracked | 1 | importgraph | [agents_test](../scripts/agents_test.py), [cli_test](../scripts/cli_test.py) +1 |
| [mind_verifier](../scripts/mind_verifier.py) | Optional entitlement verification for customer-controlled Mind execution | 1 |  |  |
| [model](../scripts/model.py) | `headron model` — which rung answers each typed judgment, read from the attached student bundle | 1 | modelpack | [model_test](../scripts/model_test.py) |
| [modelpack](../scripts/modelpack.py) | modelpack — the student rung's loader: read a verified micro-pack bundle and answer from it | 1 |  | [model_test](../scripts/model_test.py) |
| [nativetools](../scripts/nativetools.py) | native_agent_tools_are_kept: Headron is ADDED to an agent runtime's layer and never removes a tool from it | 1 |  | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [orphans](../scripts/orphans.py) | Dead harness code: a top-level function or class that nothing in the tree names but its own definition | 1 | importgraph | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [pipeline](../scripts/pipeline.py) | State-to-action pipeline — finite state machine: INGEST → CLASSIFY → VERIFY → EXIT | 1 | decide, reflex | [pipeline_test](../scripts/pipeline_test.py) |
| [plantcheck](../scripts/plantcheck.py) | plants_can_still_apply: every mutation anchor in the planted suites still matches the file it aims at | 1 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [processpolicy](../scripts/processpolicy.py) | Declared workflow records and their stopping conditions | 1 | agentpolicy |  |
| [receiptsign](../scripts/receiptsign.py) | Who wrote a receipt: a detached SSH signature over its exact bytes | 1 | receipt | [receiptsign_test](../scripts/receiptsign_test.py) |
| [scoreboard](../scripts/scoreboard.py) | What the benchmarks measure, as a floor that only rises: one row per metric, simple enough to act on | 1 |  |  |
| [shellsplit](../scripts/shellsplit.py) | The shell-string helpers shell_verdict reads: top-level statements, pipeline stages, heredoc bodies | 1 |  |  |
| [textguard](../scripts/textguard.py) | Characters in tracked text that a reader cannot see, or cannot tell apart | 1 |  |  |
| [treeformat](../scripts/treeformat.py) | Working-tree formatting and blame-history checks | 1 | gitobject |  |
| [workflowbench](../scripts/workflowbench.py) | Does Headron change what agents DO — alone, and when one hands work to another? Measured, per model | 1 | abtest, agentpolicy, dirscope | [atlas_test](../scripts/atlas_test.py) |
| [yamlshape](../scripts/yamlshape.py) | yaml_prose_is_quoted: prose inside a YAML flow collection is quoted, so a comma cannot silently split it | 1 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [agentbench](../scripts/agentbench.py) | Does an agent FINISH more real tasks with Headron? The arm every other bench here marks NOT RUN | 0 | agentpolicy, atlas, knowledge | [agentbench_test](../scripts/agentbench_test.py) |
| [agentrun](../scripts/agentrun.py) | The reference runner: the one caller in this tree that executes anything under the policy | 0 | agentaudit, agenteffects, agentpolicy, headronlang, knowledge, runtime | [agent_test](../scripts/agent_test.py) |
| [astshape](../scripts/astshape.py) | astshape — structural duplicates and code blobs, by AST rather than by text | 0 |  |  |
| [atlasci](../scripts/atlasci.py) | What a consuming repository's pull request requires, resolved against a pinned atlas | 0 | agentpolicy |  |
| [bench](../scripts/bench.py) | Does using the atlas actually help? Measured where it can be, and REFUSED where it cannot | 0 | agentpolicy | [atlas_test](../scripts/atlas_test.py) |
| [brainstorm](../scripts/brainstorm.py) | brainstorm — a strategic brainstorm as a record a program can refuse: diverge, pre-mortem, converge, prove | 0 |  | [atlas_rules_test](../scripts/atlas_rules_test.py) |
| [cadence](../scripts/cadence.py) | The time-boxed session, declared once and printed as a clock — `headron cadence [--minutes N]` | 0 |  | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [claude_hook](../scripts/claude_hook.py) | Claude Code PreToolUse adapter: refuses the pushes and bypasses the repository forbids, before they run | 0 | boundedinput, gitobject | [claude_hook_test](../scripts/claude_hook_test.py) |
| [datakit](../scripts/datakit.py) | Data kit: read tables from data files, check them against a schema, trace a report's numbers | 0 | artifacts | [datakit_test](../scripts/datakit_test.py) |
| [freshness](../scripts/freshness.py) | Which parts of this tree have not been re-examined lately — measured in CONTRACT VERSIONS | 0 |  | [handoff_test](../scripts/handoff_test.py) |
| [handoff](../scripts/handoff.py) | A bounded, artifact-specific handoff — route evidence instead of a repository dump | 0 | agentpolicy, atlas | [handoff_test](../scripts/handoff_test.py) |
| [headron_edit](../scripts/headron_edit.py) | The MCP route that may EDIT — separate, opt-in, and bounded by the task contract it is started with | 0 | agentaudit, agentpolicy, headron_mcp, safeedit | [atlas_guards_test](../scripts/atlas_guards_test.py), [edit_version_test](../scripts/edit_version_test.py) |
| [installcheck](../scripts/installcheck.py) | Run the install command the documents give, in a clean home, and judge `headron doctor` by exit code | 0 |  | [cli_test](../scripts/cli_test.py) |
| [judge](../scripts/judge.py) | `headron judge` — a small decision asked as a closed question, acted on only above a declared bar | 0 | boundedinput, knowledge, model | [judge_test](../scripts/judge_test.py), [model_test](../scripts/model_test.py) |
| [links](../scripts/links.py) | `headron links`: where this release is, and what each companion reads from it | 0 | commands |  |
| [mcpsize](../scripts/mcpsize.py) | Measure an MCP `tools/list` dump against the declared per-server token band | 0 | contextcost |  |
| [mdshape](../scripts/mdshape.py) | mdshape — every Markdown file has a class, and each class has a rule: bounded, preserved, or reachable | 0 |  | [atlas_rules_test](../scripts/atlas_rules_test.py), [cli_test](../scripts/cli_test.py) |
| [packprobe](../scripts/packprobe.py) | packprobe — how many of each language pack's DECLARED commands resolve on this machine | 0 | packmanifest |  |
| [pointers](../scripts/pointers.py) | The pointer table: every name in atlas.yaml that points at something else, in one place, read by one engine | 0 | knowledge, packmanifest | [pointers_test](../scripts/pointers_test.py) |
| [privacy_guard](../scripts/privacy_guard.py) | Refuse personal data and secrets before they reach a commit, a push, or the shared history | 0 |  |  |
| [sandboxgen](../scripts/sandboxgen.py) | Generate the host sandbox a task contract needs, from config/agent-sandbox.json | 0 | headronlang | [atlas_guards_test](../scripts/atlas_guards_test.py) |
| [schedtargets](../scripts/schedtargets.py) | Every ACTIVE scheduled job's target must exist on THIS host — `headron schedtargets [--root DIR] [--platform… | 0 |  | [schedtargets_test](../scripts/schedtargets_test.py) |
| [seats](../scripts/seats.py) | Attach declared agent, model, chat, and plugin seats on this machine | 0 | atomicfile |  |
| [staleness](../scripts/staleness.py) | What was edited longest ago, and which worktrees are hung — computed from git, never typed | 0 |  | [atlas_test](../scripts/atlas_test.py), [vanish_test](../scripts/vanish_test.py) |
| [taskbench](../scripts/taskbench.py) | Does Headron make a model better at work OTHER than routing? Blind against with-Headron, per task kind | 0 | abtest, agentpolicy, providers |  |
| [worktree](../scripts/worktree.py) | Worktree-based agent isolation — each session gets its own git worktree | 0 |  |  |
<!-- END generated: module-leaves -->
