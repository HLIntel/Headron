# Failure shapes

GENERATED from atlas.yaml/agent_failure_modes, most-sighted first.

## a_check_proven_on_one_shape_of_input

- shape: a check or a compatibility claim is verified where it was tried — a whole package, one dialect, one protocol revision — then declared for every input of its kind, and refuses correct input of another shape
- looks like: a verified command, and a hook that suddenly rejects good code; a passing MCP probe, and a client that cannot connect
- tell: a correct example fails the check while a planted break in it is refused too; or every probe passes and the real client is refused
- do instead: enforce measure runs every check on every correct example first; the MCP probe asks with every declared revision, and a revision captured from a refused real client is declared by that client name

## a_quote_that_outlived_its_text

- shape: a test locates its target by QUOTING the file it plants into — an anchor, a sentence, an index call — and an edit to that file removes the quoted text, so the test crashes or silently applies nothing
- looks like: a clean `thea check` followed by a suite that dies minutes in with substring not found
- tell: the failing line is an .index( or .replace( on a literal that no longer occurs in the file it reads
- do instead: read every quoted anchor statically, before the suite runs: mutation anchors, plant tables and file quotes alike

## a_pushed_lane_nothing_will_merge

- shape: work is pushed and a pull request opened, and nothing is armed to merge it — or it is armed but DIRTY while main or another open lane already carries every patch — so it sits finished-looking
- looks like: done, from the terminal
- tell: the branch is pushed and its pull request is open, but nothing is armed to merge it, so it sits unmerged
- do instead: made STRUCTURAL, not detected — .githooks/pre-push refuses a bare push of any lane, admitting only branchstate.py --land, which pulls, rebases, pushes, opens the pull request and arms auto-merge in one step; --sync arms any open request opened elsewhere, as the gh user and never as GITHUB_TOKEN, whose merges would silence every workflow on main

## an_interpreter_below_the_declared_floor

- shape: a script is run by a bare `python3` that resolves to an interpreter older than pyproject's requires-python, so a stdlib module the floor guarantees (tomllib, 3.11) is missing and the run dies on import
- looks like: ModuleNotFoundError: No module named 'tomllib' from atlascore.py or safeedit.py, read as a broken contract or a missing dependency
- tell: the traceback's interpreter path is a system Python (3.9) while pyproject.toml says >=3.11; the same command under uv run passes
- do instead: atlascore refuses below the floor as NOT RUN (exit 2) naming the floor and the uv run command; run repository scripts as `uv run python scripts/<x>.py` or the installed launcher

## a_generated_block_whose_input_is_the_index

- shape: a generated block computed over the TRACKED set drifts the instant `git add` changes that set, so regenerating before staging leaves the block stale and the commit is refused by a tree that was green a moment earlier
- looks like: a pre-commit refusal nobody can reproduce, because re-running the check after the refusal passes — the index moved between the two
- tell: the same block named twice in one session, each time after staging
- do instead: regenerate AFTER staging and stage again — stage, `check --fix`, stage. The index is an input, so it is part of the run rather than something done to the run

## an_allowed_binary_whose_argument_nothing_adjudicated

- shape: a control checks argv[0] against an allowance and a denial list and stops, so a path carried in the command's ARGUMENTS reaches a decider that was never called
- looks like: a narrow-tools control with a correct sandbox decider beside it
- tell: the sandbox function is correct and complete, and grep finds no call site that passes it a command argument
- do instead: argument_paths resolves the paths a command carries and hands each to the same path_verdict the sandbox control already names, so there is no second copy of the rules

## a_success_rendering_read_as_an_answer

- shape: a call is counted as answered because its status code or exit code said so, while its payload carried nothing — and the empty answer is then scored as a WRONG one
- looks like: a successful request with a token count beside it
- tell: one answer path in the same file refuses an empty payload and another returns it, so the predicate was written twice and one copy is missing a clause
- do instead: every answer path judges its payload through one predicate that names the paths it requires, and a numeric zero or false stays an answer because those are values

## a_fixture_that_names_what_it_could_read

- shape: a test anchoring on a literal — a version, a budget, a file list — that later moves
- looks like: a passing test that planted nothing
- tell: the test's hard-coded value no longer exists in the file, so its planted edit changes nothing and the test still passes
- do instead: atlas_test.mutated, which refuses when the planted text equals the original

## a_guard_that_crashes_on_another_guards_input

- shape: a checker raising on malformed input that a different checker exists to report
- looks like: a broken harness, so the real finding is never reached
- tell: one checker throws a traceback on malformed input, and the checker whose job is to report that input never runs
- do instead: parse-first in atlas.check, and each guard catching and continuing

## an_instrument_wrong_in_its_scope

- shape: correct arithmetic over the wrong set — summing three conventions no runtime loads together, counting instruments no consumer installs
- looks like: a precise number, which is why it is believed
- tell: every sum is correct, but it was computed over the wrong set of items — and the set it MISSED is often the larger one: a per-turn cost counter that measured FILES on the entry path while tool schemas arriving over a protocol at runtime, 30,855 tokens of them, sat outside its window entirely; read as the total, the same counter predicted a fresh first turn near 21k tokens against 74k measured, and its override matcher read bare skill names while plugin skills are keyed plugin:skill, so 338 overridden tokens were still charged
- do instead: every instrument declaring what it does NOT measure, and a closer that disagrees

## a_guard_matched_on_the_tool_name_rather_than_the_act

- shape: a pre-edit guard keys on the NAME of the tool that edits — Edit, Write, MultiEdit — and the agent writes the same files through a shell heredoc instead, so the guard never fires. It is present, correct, reachable, and blind to the path actually taken
- looks like: an agent walking into the exact traps the place it is editing has already recorded, while the guard that would have handed it that list reports nothing, because reporting nothing is what it does when it does not match
- tell: the guard has no misses to show. A matcher that never fired and a matcher that fired and found nothing print the same silence — and the agent's own edit log is the only place the mismatch is visible
- do instead: match the ACT, never the tool that performs it — a matcher that names tools is a roster of renderings, and the shell is always the rendering nobody enumerated. Where the matcher cannot be widened, write repository files through the tools the guard does watch

## a_flow_value_split_on_a_comma

- shape: an unquoted comma inside a YAML flow mapping ends the value; the rest becomes a key holding null, and a loader that only refuses duplicates accepts the truncated record
- looks like: a declaration that reads complete in the file and is half missing once loaded
- tell: the loaded record has a key made of words and no value, and the field it split from ends mid-sentence
- do instead: the strict loader refuses a flow entry with no value at parse time, and values are GENERATED by `safeedit.py quote`, proven to read back in plain and flow position — never hand-quoted

## a_generator_that_reads_the_disk_not_the_tree

- shape: a generator or count walks the directory on disk, so local build output and ignored files enter a document that CI, on a clean checkout, renders differently
- looks like: a green pre-commit and a red Contract job on the same commit
- tell: the generated table links to files under an ignored build directory that exist only on the machine that ran the example
- do instead: example walks read the tracked tree. DECLARED BLIND SPOT, a promise to come back — about 25 other globs still walk the disk, over directories no build writes into today

## a_count_typed_into_prose

- shape: writing a number into a document instead of generating it or naming the instrument
- looks like: an accurate sentence, on the day it is written
- tell: a number in a document disagrees with what the tool prints today, and no tool generated that number
- do instead: the generated blocks, and a reviewer who asks where a number came from

## a_blanket_rule_over_unlike_things

- shape: one directive applied to a suffix or a directory whose members are not the same kind
- looks like: a tidy one-line fix that over-corrects the other way
- tell: after the fix, files that were fine before start failing, because the rule matched a suffix or folder whose members are not alike
- do instead: classification per kind, and a measurement taken after the rule rather than before

## a_generated_block_carrying_a_relative_link

- shape: a link inside a block that is rendered into more than one place, or moved between them
- looks like: a working link, in the document it was written in
- tell: the same generated block links correctly in one document and to a missing page in another
- do instead: relative_link_errors, for a block registered in MORE THAN ONE file, where the link cannot be correct for all of them. A block with one home is left alone — the first version of this guard refused those too and stripped 76 working links before the count showed it, which is a guard damaging the tree to satisfy itself

## a_roster_that_resolved_to_nothing

- shape: a glob, list or query that matches zero and proceeds — a build with no targets, a scan with no files, a campaign with no cases
- looks like: a clean pass, identical in every character to a real one
- tell: the check reports success while its list of targets was empty: zero files matched and it proceeded
- do instead: every roster printing its count and refusing a zero — the fuzz build, exrun's coverage line, the example-coverage ratchet and the instrument roster

## a_backtick_inside_a_double_quoted_shell_string

- shape: writing a commit message, PR body or any text with `backticks` inside double quotes — the shell runs the contents as a command and substitutes its output, usually empty
- looks like: a successful commit. The text is simply GONE from the message, and nothing warns. WORSE, measured twice at contract 3.25.0 — when the substituted output carries a newline or a shell metacharacter, git reads the fragments as PATHSPECS and refuses the commit outright — so the files stay uncommitted while the agent reports success. A failed commit and a commit nobody made are indistinguishable from the command's own output; both were caught only by a later `git status --porcelain` showing the work still dirty
- tell: a phrase that was inside backticks is missing from `git log`, or the commit refused with a pathspec error while the agent reported success
- do instead: a quoted heredoc for every multi-line message, which this repository already uses almost everywhere; the one that slipped used -m with double quotes and lost a phrase into git history, where it cannot be corrected without rewriting shared history

## a_verdict_printed_and_not_gated

- shape: a script prints each rung's exit code and then proceeds regardless — the verdict is displayed, never obeyed
- looks like: a thorough check. At 2.28.0 astshape printed rc=1 for a duplicate structure and the same one-liner committed and landed anyway; CI's required Contract job is what held the merge
- tell: the red verdict is on screen in the same output as the "armed" or "committed" line after it
- do instead: .githooks/pre-commit refuses a commit on a red fast rung, and branchstate --land runs the gates in a clean checkout of HEAD and refuses to push on red — no flag skips either. In an agent's own shell, `thea shell` refuses a verdict piped into a filter without pipefail (3.42.0), called by the runtime's PreToolUse hook — the third sighting was `atlas.py check | tail` exiting 0 over a leak

## a_suffix_read_as_the_interpreter

- shape: a file's checker is chosen by its suffix, and the file's first line names a different interpreter — `.sh` under `#!/bin/zsh` is judged by `bash -n` and refused for correct zsh
- looks like: a real syntax error in 19 scripts at once, each on a line that runs every day
- tell: every refused file shares a shebang the route never reads, and each refusal names that shell's syntax
- do instead: the interpreter the shebang names chooses the route and the gate, through one reader (atlas.yaml/routing_policy/shebang_dialects); the third sighting was `thea gate` still printing `bash -n` after the enforcement rung alone had been taught

## a_reader_written_once_per_caller

- shape: the same input — a path listing, a Python source — is read by a private copy of the reader in each caller, and each copy splits, caches or fails its own way: one crashes on a file the parse check already reports, one splits on newlines and drops a spaced path, one lists nothing outside a repository and passes
- looks like: one instrument green and another red on the same file, or a check that slows a little with every new caller
- tell: grep the reader's call (`ast.parse(`, `ast.walk(`, `"ls-files"`) outside its owning module: more than one hit is more than one dialect; a profile where one builder or walker runs once per caller is the same shape costing time
- do instead: one owning function per input, content-keyed where it caches — the parse, the walk and the command parser alike — and a parser_discipline row or forbidden_calls row that refuses the call anywhere else

## a_wait_that_matches_itself

- shape: a wait or a kill selects processes by a pattern that the waiting or killing command's own command line also contains, so it waits on itself forever or kills its own shell
- looks like: a long job still running, or an unexplained exit 144
- tell: the job's output file already holds its final line while the wait loop keeps sleeping
- do instead: the harness's background-task notification or a PID instead of a hand-written wait loop; a `pgrep -f` pattern bracketed on its first character (`[s]leep`) cannot match its own shell, and `thea shell` refuses the unbracketed form (3.44.0)

## a_check_satisfied_by_a_rendering

- shape: a check asks whether a value appears ANYWHERE in a file, so any rendering of it satisfies the check while the one line that states it is stale
- looks like: a passing version check
- tell: the navigation line names an old version, and the check passes because a generated table in the same file carries the new one
- do instead: version_sites names a pattern for the one line that states the version

## a_non_answer_scored_as_wrong

- shape: a scorer maps a refusal, a decline or an unparsed format onto WRONG, so the number measures the prompt or the parser instead of the model
- looks like: a large, clean improvement
- tell: a blind arm scores near zero on a yes/no question, below a coin flip, because the model declined to guess
- do instead: score returns None for a non-answer, and a run holding any None is refused

## a_suite_that_writes_the_owners_state

- shape: a test harness that inherits the owner's state directory, so every planted refusal, verify and session lands in the record the README counts as use
- looks like: busy real usage; it is the suite's own plants
- tell: a ledger or registry under the owner's home holding a planted fixture's name, or one session re-firing the same refusal shape dozens of times
- do instead: the planted suite pins THEA_HOME to its own temporary directory at start, and a planted case refuses when the ledger path resolves under the owner's home

## a_turn_spent_rewording_instead_of_building

- shape: an agent treating a failing cap as a writing exercise — cut a phrase, re-measure, repeat — instead of reading what the check names and building the fix once
- looks like: steady progress; it is the same measurement taken several times
- tell: a ratchet breach fixed by trimming and re-running the check, once per sentence, until it passes
- do instead: a breach names its largest parts, so the cut is chosen once; measure every cap BEFORE editing and plan against it

## a_read_only_audit_that_ran_a_mutating_suite

- shape: a process that plants and restores tracked files running beside an editor it cannot see
- looks like: a clean tree afterwards, because the restore put its own bytes back over the edit
- tell: an agent told to read only ran the planted suite in a worktree another session was editing
- do instead: THEA_READ_ONLY=1 in every audit prompt, which the suite refuses, and scripted edits refusing while the suite lock is held

## a_second_declaration_of_one_value

- shape: the same fact written in two places, which agree until one is edited
- looks like: nothing, until the stale copy is the one being read
- tell: the same constant is written in two files, and after one edit they hold different values
- do instead: the version-site roster, the generated-file roster, and check refusing a declaration that exists twice

## a_cached_reading_read_as_a_measurement

- shape: acting on a page or a status that is served from a cache rather than computed now
- looks like: a failed change, so a working fix is re-done and distrusted
- tell: a page or status still shows the old value after the change landed, and a fresh uncached read shows the new one
- do instead: staleness_discipline, which names the cache and the authority for each reading

## a_derived_roster_written_out_by_hand

- shape: an instrument enumerates what it could derive from a declaration already in the tree, and its own comment argues that enumerating is the SAFER choice
- looks like: a plausible bar. It prints percentages that are individually right and a set that is incomplete, and nothing in the output says which languages it never looked for
- tell: the tool's list of items was typed by hand, and the declaration it should have read holds more items
- do instead: linguist_names, which is complete over routes because linguist_name_errors refuses a route missing from it, and a suffix table derived from the router rather than typed — 13 enumerated suffixes against 53 routed ones, measured at 2.27.0

## a_generated_page_loaded_as_a_component

- shape: a directory a runtime loads WHOLE — every .md a command, every folder a skill — is given a directory scope, so the guide this atlas generates there is loaded as a capability nobody wrote
- looks like: one more scope and one more generated guide, both green under every check this tree runs
- tell: a slash command, skill or agent named THEA appears beside the real ones after a directory gained a scope
- do instead: PLUGIN_LOADER_DIRS, whose scopes the plugin probe refuses, and lane commands shipped as user-only skills rather than as a commands directory

## a_gate_that_resolves_to_silence

- shape: a pack NAMES a tool for a role and never says what command drives it, so the gate resolves to nothing and the change merges with a gate that never ran
- looks like: a full manifest. The role is filled in, the reviewer sees a tool, and the unrunnable gate and the passing gate print the same nothing
- tell: the plan lists a gate and `thea gate` prints no command for it
- do instead: role_coverage_errors in atlasinv, which refuses any (pack, role) pair that is neither runnable nor declared `none` — 44 of 315 pairs at 2.26.0, every one closable by a command the same manifest already declared

## a_lane_on_a_replaced_history

- shape: a branch forked from a history the base later replaced; it shows as conflicted ("dirty") forever, cannot merge, and its real change is stranded — then closed, because a stuck pull request looks finished
- looks like: an old pull request nobody can merge. Pull request 90 carried an effects lattice, a name resolver and a version-claim refusal; it sat dirty for a day and was closed unported (3.41.0-3.45.0)
- tell: `thea landed <branch>` reports hundreds of unlanded commits for a lane that made two
- do instead: land a lane within its bound (branch_policy), and when `thea landed` says STRANDED, port the change by patch onto the current base the same day

## an_agent_landing_that_targets_the_atlas

- shape: a tool that lands work reads its policy and runs its git commands from the same root, so run from another repository it branches, commits and pushes against the policy's own repository
- looks like: an installed landing command that works perfectly in the repository that wrote it
- tell: every git call in the landing passes the policy root as its working directory, and nothing asks which repository the caller is standing in
- do instead: atlascore.worktree answers whose tree is changing, separately from ROOT, and refuses outside a git repository; a consumer's clean checkout runs the gates this atlas routes for its changed files; enforce.py `check --tracked` sweeps the caller's tree (enforce.tracked_here) — the second sighting, 3.43.0, swept Thea's 401 files from a consumer and passed

## a_rebase_that_runs_before_a_push_that_will_be_refused

- shape: a fetch-rebase-push chain rebases FIRST, so when the push is refused — branch protection, a missing permission, a required review — the local tip has already been reset onto the remote and the commit is no longer on the branch
- looks like: one push error, read as the only failure; the branch then reports ahead=0 and a clean tree, exactly as if nothing had been written
- tell: a push or gate error and ahead=0 in the same run, and the commit is reachable only from `git reflog`
- do instead: dry-run the push (`git push --dry-run`) or read the branch protection BEFORE rebasing

## a_prerequisite_reported_as_the_capability

- shape: one of several conditions a capability needs is satisfied and the capability is reported working — a bridge registered with no client installed, a key present but unauthorised, a route added that nothing calls, a roster widened that no reader reads, a model listed by a provider's roster or a health endpoint answering 200 read as the model being able to serve the task
- looks like: an honest, verified fix that names correctly the one thing it actually checked
- tell: list every condition the capability needs and check each one; the feature still does nothing end to end
- do instead: a fix is reported as PREREQUISITE SATISFIED until something has been driven through it

## a_round_trip_that_drops_what_the_format_allowed

- shape: a config is read with a permissive parser, edited as objects, and written back with a STRICT serialiser that cannot represent what the format allowed — comments, key order, trailing commas. The parse succeeded, the write succeeded, and the file is now missing the part no schema describes
- looks like: a clean diff of the change you intended, with a suspicious number of DELETIONS beside it
- tell: the added and removed line counts are both large for a change that only appends; removed lines are comments, or are identical to added ones except for encoding
- do instead: a JSONC or YAML file with comments is edited as TEXT, never as a parsed object graph. The comments are the load-bearing part - they record why a line exists, which no key name carries

## a_second_claimant_of_a_singleton

- shape: two instances of a control-plane daemon — one started by the desktop app, one from a terminal or a package manager's service — both claim work from the same queue, so tasks run twice, race on the same worktree, or are acknowledged by one and executed by neither
- looks like: duplicated or vanished work with every process healthy and every probe green
- tell: count running instances by command line: more than one, each holding a claim; the claim log shows the same task accepted twice
- do instead: a singleton takes an exclusive lock or lease before claiming anything and exits when it cannot, and a start from a second surface attaches instead of spawning; the host runs `hostshape.py singletons` over its declared singletons at session start and on a timer (enforced locally)

## a_finished_worker_leaves_its_resources_running

- shape: a worker reports done while something it started lives on — a background loop reparented to init, a linked worktree on a landed or deleted branch, a task directory of an archived agent, a container VM running with no container in it — and nothing that remains owns stopping it
- looks like: a machine that is hot, full or slow with every task marked complete and every agent idle
- tell: processes with parent pid 1 and no service label whose command is a test runner, a shell wrapper or a scratch script; worktrees whose branch has no commit outside the default branch; task directories whose owner is archived or whose issue is closed; a container runtime whose VM is up with zero containers, still holding memory and a listening resolver
- do instead: closing is verified, not asserted: the worker stops and reaps what it started, removes its worktree, and a sweep run at session end and on a timer names every leftover by owner and stops the ones that are provably finished

## a_hook_that_runs_a_deleted_script

- shape: a harness hook or status line names a script by path, the script is deleted or moved, and the hook keeps firing — its error swallowed by a redirect or a non-blocking exit — so the check it ran stops while every session starts normally
- looks like: a quiet session with one guard never heard from again
- tell: a path in a hook command that does not exist on disk; the last line that guard ever logged predates the commit that removed its script
- do instead: deleting a script and every hook, status line and scheduler entry that names it in the same change, and a sweep that resolves every path a hook or scheduled job executes or changes into — on the host that runs it — and fails on one that is missing; a wrapper never turns a missing target into exit zero

## an_unallowlisted_tool_surface_that_grows

- shape: an agent's tool surface — remote connectors, MCP servers, plugins, skills — grows without a declared allowlist; every surface costs its schema or description on every turn and dilutes tool choice, so results and token efficiency degrade silently
- looks like: more capability: each addition reads as helpful and nothing fails
- tell: the count of loaded tools, plugins and skills per agent rises with no declared allowlist entry naming why, and several loaded surfaces duplicate a CLI already on PATH
- do instead: a declared per-agent allowlist naming why each surface is loaded and its cli_equivalent, and a guard that reads every harness's live configuration and fails on anything loaded but not allowlisted, or loaded as MCP when a CLI equivalent is declared

## a_cache_sweep_that_deletes_a_source_file

- shape: a cleanup treats a cache directory as wholly derivable and deletes it, and the only copy of a hand-written source — a build recipe kept beside the artefact it builds — goes with it
- looks like: a reclaimed cache, and weeks later a rebuild that cannot find its recipe
- tell: a source-shaped file (a recipe, a script, a config) under a cache path, and a live reference to that path
- do instead: a sweep deletes only what is re-derivable: `hostshape.py sweep <paths>` refuses any source-shaped file outside a declared derivable directory, and a source file never lives under a cache (enforced locally)

## a_value_quoted_by_hand

- shape: text is placed inside a quoting context — a YAML scalar, a shell string, a pattern — by typing the quotes, and a character that context reads as syntax (an apostrophe, a colon, a comma, a backtick) ends the value early
- looks like: a one-line ledger or config edit after which the whole file stops parsing, or parses short
- tell: the value was typed between quotes rather than printed by the format's own emitter, and the breaking character sits inside prose
- do instead: every value is generated: `safeedit.py quote` for one scalar, `safeedit.py entry` for a ledger entry, a quoted heredoc for a shell message

## a_shared_lock_retried_once_against_siblings

- shape: a waiter retries a shared lock once after it frees, and a sibling waiter takes it first, so the waiter gives up having done nothing
- looks like: land NOT RUN twice in a row, nothing pushed, while every other session's suite kept running
- tell: the land output prints 'landing again' once and then NOT RUN on the second attempt
- do instead: land loops on NOT RUN each time the suite lock frees, under one LAND_WAIT deadline across every retry

## a_worktree_inside_the_tree_it_copies

- shape: a worktree is created inside the repository it copies (a desktop default puts it under .claude/worktrees), and every walk rooted at the repository reads the copy as this tree's source
- looks like: a planted-suite case fails on modules no branch holds, and a privacy scan lists the same file twice
- tell: a failing path begins with .claude/worktrees/ or another directory that holds its own .git
- do instead: files_under reads git's own file set and prunes every directory holding a .git; the agent hook lane-guard refuses a git worktree add into a work tree; worktrees live beside the repo in <repo>-wt/

## a_partial_edit_set_from_a_failed_assert

- shape: a script editing several files asserts on an anchor part-way through — the files before the assert are written, the rest are not, and the tree is left half-changed while the traceback scrolls past under a later tool's green
- looks like: a clean contract check over a rule nothing checks. The declaration landed, its enforcer did not, and every count still printed
- tell: a LINTER's pass read as covering the whole edit. Ruff said all checks passed because what it linted was valid — it had no opinion about the half that was never written
- do instead: resolve every anchor BEFORE writing anything, or give each file its own run; and never read a later tool's verdict as coverage of an earlier tool's failure

## a_restore_from_a_stale_journal

- shape: a plant journal left by a killed run is applied AFTER its tree was refreshed from elsewhere, writing pre-plant bytes over newer content that the journal knows nothing about
- looks like: a file reverting to an older version with no edit in the diff that anyone made, and a gate failing on content the author never wrote
- tell: a restore that reports success on a tree it was not taken from
- do instead: restore BEFORE syncing, never after — a journal describes the tree it was taken from, so applying it to a different one is a write, not a repair

## a_walk_over_paths_another_session_owns

- shape: a walk lists paths another session owns (worktrees, temp lanes, lock holders), then opens each one; a sibling removes one between the listing and the open, and the walk raises instead of reporting it
- looks like: a planted suite that dies with FileNotFoundError on a temp directory no file in the diff names, and passes on the rerun
- tell: the missing path is under a temp root or another lane, and `git worktree list` no longer shows it
- do instead: a listed path is a claim, not a handle: the per-path read catches the vanish and reports the row PRUNABLE; `git -C <path>` (exit 128) is safe, `cwd=<path>` raises before git runs

## a_working_directory_snapshotted_on_every_turn

- shape: an agent snapshots or indexes its working directory once per turn, so the SIZE OF THE cwd becomes a per-turn cost — and the cost is charged to the model's apparent latency, where nothing about the prompt, the token count or the tool roster predicts it
- looks like: a slow agent that still answers correctly; a status of BROKEN on a binary that works
- tell: turn time is flat across wildly different context sizes, and the agent's own log names the directory — halving the context made the turn SLOWER, while the bare model served 31k tokens in 2.2s
- do instead: refuse a tree-sized cwd at dispatch (home, a filesystem root, a temp root) and pass a project directory; measure one prompt across several cwds before blaming the model or the tokens

## a_fault_that_fails_fast_masking_a_slower_correct_path

- shape: a broken artefact makes an expensive operation abort early, so the system is FASTER while faulty; repairing the artefact restores the full cost and the fix reads as a regression
- looks like: a correct cleanup that made things measurably worse, and a temptation to revert it
- tell: removing a stale lock, cache or marker increased the time it was supposed to reduce
- do instead: after removing a mask, RE-MEASURE — a mask hides a cost rather than removing it, so the number to fix is the one the mask was hiding, not the mask

## a_commit_hash_read_as_the_content_it_carries

- shape: a lane is judged merged by whether its commit HASHES reach the base, and a squash merge lands the same content under a new hash
- looks like: a lane reported active with work ahead of the base
- tell: commits ahead of the base, and `git diff` against the base is empty
- do instead: compare the tree the lane carries with the base, never only the commit count

## a_run_that_loses_everything_on_one_hang

- shape: a batch has no bound on a call, or does not catch the bound expiring, and writes results only at the end — so one hung call ends the run and discards every result already finished
- looks like: a long run that "failed", with nothing recorded to show for the part that worked
- tell: the output shows finished lines for earlier models, and the evidence file holds none of them
- do instead: every subprocess call carries a timeout (guarded); a benchmark catches the expiry as one non-answer and records after each model

## a_search_that_skips_what_it_cannot_see

- shape: a sweep runs through a shadowed search tool — the Claude Code shell replaces grep and find with an embedded ugrep that honours .gitignore and reads -E alternation differently — so ignored files are never searched and the sweep reports clean
- looks like: a clean sweep
- tell: a Python scanner over the same paths finds hits that grep in an agent shell did not
- do instead: a STANDING VERDICT (graduated from intake at 3.2.0) — no in-tree guard can reach the harness shell

## a_gate_that_aliases_another

- shape: many gate names resolve to one command — the plain test runner, a bare runtime, a bare build tool — so each reads as its own passed check while one run proved only the first
- looks like: broad gate coverage, every name resolving
- tell: race_detection resolves to `go test` without -race, and so do timeout, auth and contract tests
- do instead: gates_resolve_distinctly fails any collision outside gate_alias_groups, and a bare runtime or library driver resolves to absent with its closer

## a_class_that_skipped_its_base

- shape: a specialised policy class lists its own requirements and silently drops the base ones every member of the family needs
- looks like: a complete checklist for the special case
- tell: an API or security change must pass its own gates but not the compile, format and unit tests every code change needs
- do instead: profiles declare `extends`, and required_gates resolves the base first

## a_named_mechanism_that_does_not_exist

- shape: policy prose sends work to a job, file or workflow that nothing implements
- looks like: a covered case, with a place named for it
- tell: the policy says a scheduled workflow runs these examples, and the workflows directory holds no such file
- do instead: every backticked path in a document must exist, and a place is named by its path

## a_bad_result_captioned_and_passed

- shape: a result that is bad or off-goal gets a caption (a chance baseline, a footnote, "sample") and the work moves on, instead of the cause being diagnosed and fixed on the run that produced it
- looks like: an honest report — the number is true, and the defect behind it ships
- tell: a surprising score is published beside a baseline or caveat, with no miss ever printed
- do instead: taskbench refuses to record a non-answer, or an arm where Thea scores BELOW blind, and --misses prints every wrong answer so the cause is named before any number is kept

## a_mutation_planted_where_the_checker_never_reads

- shape: a test plants a defect in a source file, and the checker under test runs in the same process with that module already imported, so the planted code is never loaded
- looks like: a mutation test of a code rule
- tell: the planted file differs on disk and the in-process verdict does not move; a subprocess would see it
- do instead: plant a code-shaped defect in the object the checker receives (a parser, a record), or run the checker in a subprocess — never edit a module the running suite already imported

## a_local_tweak_that_edited_a_public_repository

- shape: a user-config path that is a SYMLINK into a tracked repository, so editing the convenient copy edits the repository with all its gates
- looks like: a local preference change, until the push is refused by a branch rule
- tell: a one-line edit to a file under ~/.claude that turns up as an unpushed commit on a public repository's main
- do instead: the shipped copy carrying its own budget, so the edit is judged here rather than discovered in a consumer's per-turn budget; and landing it through a lane like any other change

## a_plant_left_by_a_killed_run

- shape: a test that plants a defect and restores it in a finally block, killed by a timeout before the finally runs
- looks like: a real defect in the repository, found by the repository's own checker
- tell: a reviewer's verify reported a contract drift the source never contained — the planted value, verbatim
- do instead: a journal written before every plant, a check that refuses a leftover, SIGTERM turned into an exit, and --restore

## a_local_green_read_as_a_verdict

- shape: passing on this machine and reporting it as passing
- looks like: a green ladder; the absent thing is absent HERE only
- tell: everything passes on this machine, and the tool it depends on is missing on the CI runner
- do instead: continuous integration as the authority, packprobe for per-machine facts, and tool_claims, where every rung above `declared` must name the machine it was measured on

## a_shape_written_twice

- shape: two functions with different names and identical structure, each checking one roster
- looks like: thorough coverage that disagrees once one copy is fixed
- tell: two near-identical functions check two lists; a fix landed in one and not the other
- do instead: astshape, which compares canonical ASTs with names and literals erased

## an_arm_that_shipped_and_could_never_run

- shape: a module is packaged for consumers although it depends on something only this checkout has — here `git ls-files`, which an installed wheel has no tree to answer
- looks like: coverage. The capability is in the roster, in the package, and in the docs, and the first consumer to call it gets an empty result rather than an error
- tell: installed users get an empty result from a feature that works in the source checkout
- do instead: the wheel ships only the launcher, which runs the resolved atlas's own harness (3.7.0), plus wheel_import_errors, and the question that finds it — name the line that reaches it in an INSTALL, not a checkout

## a_later_definition_that_silently_wins

- shape: an edit that rebuilds a file from slices with the end index before the start duplicates a span; Python keeps the LAST definition, so every test passes over two copies of a function
- looks like: a clean test run. Nothing is wrong with either copy, and the suite cannot see that there are two — the byte ratchet caught it, four thousand bytes after the fact
- tell: a file grew by the size of one function and its def appears twice
- do instead: context_policy/install_footprint, a size ratchet that only falls, which is the only instrument here that reads a file's WEIGHT rather than its meaning

## a_tie_that_was_an_artifact_of_the_question_set

- shape: two arms of an experiment score identically and the tie is reported as a finding, when it was a property of how narrow the questions were rather than of the arms
- looks like: the strongest possible result — equal accuracy at a third of the cost. At 2.26.0, over two question kinds, routed and whole_tree tied at 98.5%; a third kind at 2.27.0 separated them, 96.8% against 97.5%, and the honest claim became a trade rather than a free lunch
- tell: two arms score identically over a question set of one or two kinds
- do instead: abtest.py asking three question kinds over every pack and reporting the gap in both directions — an arm that wins on accuracy and loses on cost is the normal case

## a_lookup_that_reparses_per_call

- shape: a new rule calls an uncached loader once per item it checks, so its cost is items times parse — correct output, and a regression nothing sees because nothing measures time or calls
- looks like: a green check that got slower. At 2.26.0 one check() parsed about 37 YAML files 671 times (73% of its wall clock) and the suite took 137s; 315 of the parses came from a coverage rule written that session. Behind it, 11 reads bypassed the strict loader, so one defect was a speed regression AND a silent duplicate-key hole
- tell: a check got slower and a profile shows one loader called once per item
- do instead: strict_yaml cached by CONTENT, forbidden_calls/yaml_loader_bypass, and a parse budget derived from the tree — each tracked YAML file at most once per check — mutation-tested by planting the cache off, which reproduces the 671 and is refused

## a_lookup_by_name_that_finds_the_dead_record

- shape: a record is looked up by a NAME that outlives it — a branch name reused after its first pull request merged — and the lookup returns the finished record instead of nothing
- looks like: every step printing ok. `gh pr view <branch>` returned the merged pull request 26, no new pull request was opened, auto-merge was armed on a merged request as an exit-0 no-op
- tell: a lookup by name returns a record already merged or closed
- do instead: _pull_request listing OPEN requests only — the open request is the identity and the name is a rendering — and land() exiting 0 only on an `armed` verdict

## a_restore_that_erases_a_concurrent_write

- shape: a test plants a defect, saves the file's bytes, and restores them afterwards — erasing anything another writer put in the file while the defect was planted
- looks like: nothing at all. An agent edited atlas.yaml while the suite ran in the background; the restore wrote back the pre-edit bytes, the entry vanished, and no command failed. Reproduced deterministically at 2.27.0 by writing inside mutated()
- tell: an edit made while a suite ran in the background is gone and no command failed
- do instead: mutated() comparing the file to what it planted before restoring — a difference keeps the other writer's version beside it and fails the run — and suite_lock, one mutating suite per worktree. The practice beneath both — never edit the tree while that suite runs

## an_anchored_insert_that_silently_did_nothing

- shape: an edit anchored on text that is not there — str.replace returns its input unchanged — and it COMPOUNDS when each new edit is anchored on the one just written
- looks like: a script that printed ok. Three failure-mode entries were each anchored on the previous; the first was erased by a concurrent restore, so the second's insert did nothing, removing the third's anchor. Three records lost, zero errors, found only by listing the keys
- tell: the edit script printed ok and `git diff` does not show the insert
- do instead: safeedit.replace_once (refuses 0 or 2+ matches), write_verified (every write read back), anchoring on a COMMITTED key and never on a sibling written in the same batch, and verifying each record by parsing the file after the write rather than by the script's exit

## a_mutation_harness_scored_over_zero_runs

- shape: a harness that reads an exit code as a verdict, so a run that never happened scores exactly like a run that failed — and a probe run in a different process vouches for it
- looks like: a perfect score. At 2.27.0 a zsh `$S:scripts` (`:s` is a substitution modifier) failed before any test ran and scored 5 of 5 mutants KILLED; fixed, the suite's own sys.path insert shadowed every mutant and scored 6 of 6 SURVIVED over the real module
- tell: every mutant is scored killed, or every one survived, though no test actually executed
- do instead: a mutant counts as killed only by the NAMED assertion written for it, beside a control run that must pass, with the import checked in the SAME process as the suite

## a_pull_that_leaves_a_half_merge

- shape: a bare `git pull` merges; on a conflict it leaves the half-merge in the working tree, and every later pull refuses with "Fix them up in the work tree" until someone resolves it by hand
- looks like: a routine sync. The first sign is a later pull failing, often in a session-start hook nobody reads, while conflict markers sit inside notes the editor renders (3.44.0, a vault synced from two machines)
- tell: git says "you have unmerged files" or "Fix them up in the work tree" on a pull nobody ran by hand
- do instead: `git pull --rebase --autostash` (or `--ff-only`), aborting on conflict and naming the files

## a_branch_judged_landed_by_its_file_list

- shape: a pull request is closed or a branch deleted as "already on main" because every file it touches exists on main — the file list says where a change went, never whether it arrived
- looks like: a careful cleanup. Every path checked out; the two closed branches carried an unshipped landing fix and a freshness gate, found only when the work was looked for again (3.41.0)
- tell: the closing comment cites file names, and no `git cherry`, diff or patch comparison appears before it
- do instead: `thea landed <branch>` before any close or delete: patch equivalence by `git cherry`, and a squashed lane counts as landed only when merging it would leave the base tree unchanged

## an_untrack_that_deletes_on_every_other_clone

- shape: `git rm --cached` removes a path from the index to stop tracking it; the next pull on every other clone DELETES the working file, because to git the path was removed
- looks like: a harmless cleanup — the file is still on disk in the clone that ran it
- tell: a diff shows a tracked directory removed with `--cached`, and the repository is pulled by another machine
- do instead: add the path to .gitignore and leave it tracked, or untrack it only after every clone holds a copy outside the repository

## a_validator_that_diverges_from_its_spec

- shape: a hand-written implementation of a published spec differs from it on a case the tree never exercised, so every check passes until the first instance that reaches the difference
- looks like: a correct schema refusing correct data. At 2.28.0 `^https://` refused every https URL because the validator used re.fullmatch — JSON Schema patterns are unanchored searches — and all eighteen existing patterns happened to be anchored at both ends. The reference cross-check that would have caught it covered manifests only, a window smaller than the defect
- tell: our own validator rejects data that the reference implementation of the same spec accepts
- do instead: re.search per the spec; the jsonschema reference run over EVERY output record, not only manifests; a standing test that the C YAML loader equals the reference on every file

## a_regex_escaped_twice

- shape: a pattern written through two layers of quoting gains a second backslash, and an escaped dot then demands a literal backslash instead of a dot
- looks like: a schema that reads correctly and matches nothing — caught only because the frozen record test validates a REAL record against it rather than trusting the schema text
- tell: the pattern contains a doubled backslash, so it matches a literal backslash and never the intended text
- do instead: validating every schema against records the repository actually produces, and copying a pattern from a definition already proven rather than retyping it

## a_claim_made_before_it_was_verified

- shape: reporting an outward-facing action — pushed, merged, landed — without reading it back
- looks like: a finished task, to everyone but the person looking
- tell: the report says pushed, merged or landed, and reading the remote back shows it did not happen
- do instead: branch_policy/landed_states, which separates committed, pushed, merged and published, and branchstate.py, which reads them back rather than assuming them

## a_probe_that_reports_absent_what_it_could_not_reach

- shape: a probe reports a live thing ABSENT because of how the probe itself was invoked, never because the thing is missing — an exact-line match flag against an embedded blob, a closed or redirected stdin against a server that needs a pipe, a token budget too small for the model to emit anything, a subcommand omitted so the tool prints usage instead of data, or a clobbered PATH so the checker never ran at all
- looks like: a confident negative, and a decision to repair what already works
- tell: THE ERRORS ARE ALL IN ONE DIRECTION — every miscall is a false ABSENT, never a false PRESENT. Nine instances in one session: a negative arriving faster than the work could take, a zero count from a tool that also printed usage, a different client returning the opposite answer to the same request, and an interpreter missing a stdlib module so the checker never ran
- do instead: probe with the client the caller will actually use, and re-probe any negative with a second client before recording it; prefer the subject's own declared self-check to a hand-rolled one; state the exact invocation beside every negative verdict so the reader can see what was and was not reached

## an_annotation_that_was_meant_to_replace

- shape: a mechanism meant to SHRINK what a model reads adds its compact version BESIDE the original instead of replacing it, so every use pays for both
- looks like: a compressor, summariser or digest that works — its output is short and correct, and it tells the reader to ignore what came before it
- tell: the added text instructs the reader to ignore or skip something already in context; context has no ignore, only replace
- do instead: a saver replaces what it shrinks (the harness's replacing field, never an added note) and keeps the full text one read away, at a path it names

## a_leading_dash_argument_read_as_an_option

- shape: a literal that begins with a dash, handed to a builtin that parses options, is consumed as an option terminator or flag and prints nothing — a YAML fence written with zsh print "---" comes out as an empty line
- looks like: a generator that runs clean and writes every file, each missing the one line that makes it parse
- tell: the generated file's first line is blank exactly where a fence or header belongs, and the generator exits 0
- do instead: print -r -- or printf for every literal that can begin with a dash

## an_addition_that_replaces_the_default

- shape: assigning one item through a control plane switches the tool into an exclusive mode, so the items it loaded by default are silently dropped rather than extended — one managed MCP server launched the agent with a strict flag that ignored its own configuration
- looks like: a narrow, intended assignment that works: the assigned server answers
- tell: after adding one entry, something that worked before the addition is missing from the tool's own inventory, and nothing reported a removal
- do instead: declaring the agent's full server set wherever the plane replaces rather than merges, so nothing it needs depends on the default

## a_guard_whose_source_became_a_pointer

- shape: a guard's canonical input file is collapsed into a pointer to its new home, the guard keeps reading the old path, and it reports NOT RUN on every run from then on while every consumer reads the status as unchanged
- looks like: an honest guard: it refuses to pass on missing input, exactly as designed
- tell: the same guard has said NOT RUN (or skipped) on every run since a date, and that date matches a commit that shortened its source file
- do instead: moving a file's content and repointing every reader in the same commit, found by grepping the old path

## a_reclaim_undone_by_the_producer_that_was_never_disabled

- shape: a derived or downloaded artefact is deleted, the space is measured and reported reclaimed, and the process that PRODUCED it is still enabled — so it is re-created on its next eligible window and the reclaim silently reverses
- looks like: a correct before/after and a real df delta, both taken before the producer next runs
- tell: the artefact returns at its original size with nobody asking for it, and its producer's setting was never read
- do instead: before reporting any reclaim, name WHAT WRITES the thing and whether that is still running

## a_silence_read_as_a_verdict

- shape: a probe that got NO RESPONSE — a timeout, a refused connection, the machine asleep — is recorded as the thing it probed being down, and a pruner then removes it
- looks like: a tidy tuning run: lanes that kept failing were retired
- tell: the retired rows all carry http 000 or null, several from the same run, and none ever answered with a refusal
- do instead: three outcomes, never two: answered yes, answered no, did not answer. Only an answer moves a verdict, and a run where most probes are silent is a blackout that changes nothing

## a_credential_typed_into_a_command

- shape: a secret is written as a literal inside a command — echoed into a keys file, passed as a flag, pasted into a block handed to someone else — so it lands in shell history, the transcript and wherever the command runs
- looks like: a convenient one-liner that sets the key up
- tell: a known credential prefix (a KGAT, ghp, sk or AKIA token) appears inside the command text itself rather than as a variable name
- do instead: refer to credentials by NAME from the keys file; a command that must set one reads it from a prompt or the environment

## a_first_idea_argued_as_the_only_option

- shape: a strategic choice is made by elaborating the first option that came to mind; alternatives appear only to be dismissed, doing nothing is never costed, and a one-way door is walked through without anyone owning it
- looks like: a confident plan with a rationale
- tell: the plan names no option it rejected, no signal that would make it wrong, and no one who approved an irreversible step
- do instead: a brainstorm record: at least three options with a do_nothing baseline, scored on declared axes, each pre-mortemed with a kill signal, and a choice no other option dominates

## a_command_handed_over_with_an_assumed_path

- shape: a command block is handed to a person to run on THEIR machine naming paths the author never saw there, so it fails on the first line that assumed
- looks like: a copy-ready block
- tell: no such file or directory on a path the author inferred from a convention, never listed on that machine
- do instead: resolve paths inside the command (`thea --where`, `git -C "$(...)"`, a search) or name only paths seen on that machine

## a_shell_override_bypasses_audit_shebang

- shape: an agent runs an audit through a shell other than its declared interpreter, so shell-specific syntax aborts before the audit observes its target
- looks like: a closing audit command that exits nonzero without reporting its intended verdict
- tell: the audit names its required interpreter and rejects the supplied shell before any target observation
- do instead: execute an audit directly so its shebang selects the interpreter; use an explicit interpreter only after reading the script header

## a_guard_that_passes_when_its_input_is_missing

- shape: a guard answers a MISSING input the way it answers a clean one — `if not path.exists(): continue` or `return []` — so deleting, renaming or never creating the file it checks turns the guard green
- looks like: a guard that has passed on every run since a move, with nothing in its output to say it read nothing
- tell: delete the input and run the guard: it still exits 0. A clean pass and a pass over nothing print the same silence
- do instead: a guard refuses an absent input, or names the other guard that refuses it; absence is a finding unless the declaration says it is the valid state

## a_window_declared_past_what_the_lane_serves

- shape: a harness is told its context window is larger than the serving lane actually accepts, so the compaction threshold — a fraction of the DECLARED window — is never reached; each turn carries the whole history, and the session grows until the lane rejects a request
- looks like: a long session that was fine, then every request refused as too long, with compaction never having run once
- tell: per-turn input tokens rise monotonically across the session and no compaction event appears in the log; the declared window exceeds the lane's served maximum
- do instead: declare the window as the MINIMUM of what the model supports and what the serving lane accepts, and set compaction against that number

## a_stream_delta_missing_its_identity

- shape: a provider streams a tool call whose delta carries no id — or an id only on the first chunk — and a client that keys calls by id drops, merges or misattributes it; the tool never runs and the turn ends as if the model chose not to call
- looks like: a model that "refuses" to use tools on one provider and uses them correctly on another
- tell: the raw stream shows a tool_call delta with an empty or absent id; the same prompt against a second provider produces a call
- do instead: key streamed tool-call deltas by their index within the choice, assign an id when the provider omits one, and refuse a finished call that still has none rather than dropping it

## a_heartbeat_that_reports_liveness_not_health

- shape: an unattended host sends a periodic beat that proves only the beat ran — memory, disk, a port — while its scheduled work is dead: a timer enabled but never armed, jobs ending on timeout, a job runner logging errors. The alerter watches for a MISSING beat, so a host that beats on schedule over dead work is green forever
- looks like: a monitored host with a recent, cheerful heartbeat and no alert ever sent
- tell: the beat payload names no scheduled job; the newest run of the hourly audit predates the beat by hours; non-zero exit codes in the run log that nothing reads
- do instead: the beat is fail-closed: it is sent only when an audit newer than its own max age passed — audit FAIL, audit stale or audit missing sends one FAIL beat and then withholds, which turns any failure into the missing-beat alert the alerter already proves. The audit itself fails on an enabled timer that is not armed, a failed unit, a non-zero run since the last audit, an errored job, and an empty roster

## a_fixed_context_that_grows_unmeasured

- shape: the fixed context a harness loads before the first prompt — connectors, plugins, skill and tool descriptions — grows with every addition and nothing measures it, so a session starts most of the way to its window and every turn pays for it
- looks like: sessions that feel slower and compact sooner, with no change anyone can point at
- tell: the first-turn input token count, read from a fresh headless session, is a large fraction of the window; no record says what it was last week or what it may be
- do instead: a declared per-harness first-turn budget that only ratchets down, measured by a scheduled headless probe; `hostshape.py baseline <record>` fails over budget, on a stale or missing reading, and on a budget raised without a reason (enforced locally)

## a_blocking_native_dialog_hangs_the_automation

- shape: an automated click opens a native confirm or alert; the page's script thread blocks on it, the automation call times out, and a blind retry queues a second hang behind the first while the tab stays frozen
- looks like: a flaky browser tool that times out on one button and works on every other
- tell: the timeout follows a destructive or confirm-style control; a screenshot shows a modal the protocol cannot see
- do instead: a timeout from an interactive surface is classified BLOCKED, never transient — inspect the surface's state or dismiss the dialog, and trigger such controls asynchronously and poll

## a_worker_killed_mid_write_leaves_partial_state

- shape: a worker is killed mid-task — an outage, a cap, a crash — after writing some of its edits and before verifying them; whoever resumes cannot tell which step was finished, and the partial write is built on or reported done
- looks like: a lane that resumed cleanly by hand and fails a gate two steps later on an edit nobody remembers making
- tell: a step was begun and nothing records it verified; the resume started from the task list, not from the journal
- do instead: each worker journals begin and verified per step (`hostshape.py step`); `thea resume` names the last unverified step and re-verifies it before anything else, and `hostshape.py resume` fails while one is open

## an_autosnapshot_sweeps_in_flight_edits

- shape: a scheduled snapshot commits a shared checkout while other writers are mid-edit, so their half-done work lands in history under the snapshot's name, before their own verified commit
- looks like: a tidy auto-commit that later turns out to contain a broken, unfinished change
- tell: the snapshot commit touches paths another writer was editing at that minute; that writer's own commit follows with a smaller diff
- do instead: the snapshot job runs `hostshape.py snapshot` first and skips while any journaled step is unverified or the index is locked (enforced locally)

## a_self_update_that_leaves_a_placeholder_binary

- shape: a self-updating tool replaces its binary with a stub or removes its link mid-update, and the next session finds the command missing or a few hundred bytes that cannot run
- looks like: a tool that vanished overnight with nobody having touched it
- tell: the file at the command's path is far smaller than any real build, or the link is gone; the update log ends without a success line
- do instead: after any update, `hostshape.py binary <path>` and a capability probe that runs the tool on real work; pin the command to one install owner (enforced locally)

## a_model_config_change_without_an_eval

- shape: a local model's serving configuration — cache quantisation, attention kernel, context size, a rebuild — changes and ships with no eval, and the task the model serves regresses the same day
- looks like: a faster model that is quietly worse at its one job
- tell: the config change and the first failing task run share a day; no eval record is newer than the change
- do instead: every model or serving change is logged, and `hostshape.py changes <log>` fails until a CAPABILITY probe of that model passed after it — a listing or a version check does not count (enforced locally)

## unpushed_lanes_past_their_bound

- shape: lanes hold unpushed commits long past the declared bound, because the instrument that measures the bound prints its breaches and nothing that ends a session reads its exit code
- looks like: a dozen quiet branches, each one somebody meant to come back to
- tell: the lane report lists branches tens of hours past a bound of hours, and the session-end check passed
- do instead: `verify` carries the lane bound as a row, so a breach fails the done hook instead of scrolling past it

## app_state_entering_a_notes_repo

- shape: a notes repository stages its editor's own state — plugin code, themes, workspace layout, app caches and databases — beside the notes, so every sync commits churn no person authored
- looks like: a notes history full of hash-named and minified files
- tell: staged paths under the editor's dot-directory: plugins, themes, workspace, cache
- do instead: application state is ignored by declaration (`host_shapes/app_state_globs`), and the notes repository's pre-commit runs `hostshape.py app-state` (enforced locally)

## a_work_tree_that_contains_home

- shape: a repository initialised at the home directory, or above it, makes every project and every keys file under home part of one work tree, so a commit run from the wrong directory sweeps credentials and other projects in
- looks like: a staged diff of thousands of files, keys among them, from a directory that looked like a project
- tell: `git rev-parse --show-toplevel` from home answers home itself or one of its parents
- do instead: `hostshape.py home-repo` fails while home sits inside a work tree, and a probe that cannot answer is refused, never read as clean (enforced locally)

## a_filesystem_mcp_rooted_at_cwd_not_its_config

- shape: a filesystem tool server takes its allowed roots from the working directory it was launched in rather than its configuration, so from one cwd it serves the configured paths and from another it denies them
- looks like: a tool that works in one terminal and is denied in another, on the same configuration
- tell: the denied request names a configured path; the tool's reported roots equal the launch cwd
- do instead: pin the roots in configuration, and probe every harness's tool from at least two cwds, one outside every configured root; `hostshape.py roots <record>` fails on any drift or a one-cwd probe (enforced locally)

## a_model_rebuild_that_drops_the_chat_template

- shape: a model is rebuilt from a minimal recipe instead of the live model's own, and the chat template collapses to the bare prompt, so the model loses its roles and answers every instruction as free text
- looks like: a translator that writes essays; tuning knobs are blamed first
- tell: the rebuilt template is the prompt placeholder alone; an A/B that restores only the template restores the task
- do instead: rebuild only from the recipe exported from the live model, refuse a prompt-only template (`hostshape.py template`), and run the capability probe after the rebuild (enforced locally)

## a_sentinel_two_readers_disagree_on

- shape: two consumers read one file and each decodes its placeholder value (a dash, an empty cell, a none) on its own, so one treats it as absent and the other as a value
- looks like: two reports over the same table that disagree on a row nobody edited
- tell: the sentinel is a literal in more than one reader; no single function owns its meaning
- do instead: one shared reader owns the sentinel; plant a sentinel row in every consumer test

## a_required_kind_added_without_its_fixture

- shape: a guard grows its required set by one kind and its valid fixture is not given one of that kind, so the passing cases of its suite start failing
- looks like: a guard suite that turns red the commit after an unrelated-looking widening
- tell: the failure names a zero count of the newest required kind
- do instead: add one of each required kind to the valid fixture and run the guard suite in the same commit that widens it

## a_contract_repaired_one_named_field_at_a_time

- shape: a client rejects a payload, the repair fixes only the field the error named, and the next run fails on the next field
- looks like: a sequence of one-line fixes, each followed by a new validation error
- tell: consecutive errors from one validator, each naming a different field
- do instead: list every field the validator checks and repair them all in one change, proven by one accepted payload

## an_artifact_written_that_nothing_reads

- shape: a generated file is rewritten on every change and no code reads it, so it costs churn and proves nothing; agreement.lock hashed atlas.yaml bytes, moved on every comment, and its only consumer was the drift check that regenerated it
- looks like: a lockfile kept current by the generator
- tell: grep finds the file in the generator and in no reader; it changes in every commit
- do instead: the lock is one digest per parsed section and doctor and the land refresh diff the installed CLI against it

## a_passed_verdict_recomputed_on_identical_content

- shape: a gate verdict is recomputed for content it already judged — the same tree, the same gates — because the verdict was keyed to the attempt, not the content
- looks like: a land that waits behind every other lane's suite again after a push or forge refusal
- tell: the refused land's tree hash equals the tree whose suite passed minutes ago
- do instead: clean_checkout_errors remembers a PASS by sha256 of the tree and gate argv in the git common dir; a failure or NOT RUN is never remembered

## a_negative_control_built_from_matchable_words

- shape: a negative control is written in words the matcher can match, so a later real row shares two of them and the control fails for the wrong reason
- looks like: a suite that dies minutes in on a probe that was never about the change
- tell: the noise probe returns a real row, and that row was added in the same change
- do instead: a noise probe is tokens no ledger can hold, never words; lesson_flow_cases asserts it returns nothing

## a_home_folder_that_is_a_repository

- shape: the home folder holds a .git (a clone of a public repository with an unborn branch and no tracked files), so every folder under home that is not its own repository resolves its top level to home, and its worktrees hang off that hidden .git
- looks like: `git rev-parse --show-toplevel` in a tool-config folder prints the home folder instead of failing, and `git status` there lists the whole home tree as untracked
- tell: the home folder has a .git entry; `git worktree list` from a worktree names the home folder as the main tree with HEAD 0000000
- do instead: thea shell refuses `git init` and `git clone` into the home folder. To repair: check every worktree for uncommitted work and landed state, `mv ~/.git ~/Projects/<name>.git`, set core.bare true, then `git worktree repair`. With extensions.worktreeConfig on, the shared core.bare=true leaks into every worktree (exit 128 "must be run in a work tree"), so each worktree also needs core.bare false in its own config.worktree; `git branch -d` then judges merged against the unborn HEAD, so confirm with `merge-base --is-ancestor <b> origin/main` before `-D`

## a_blocked_listing_read_as_absence

- shape: an agent hunts for directories a sweep stopped listing and lists the Trash with stderr discarded; macOS privacy control denies the listing, the error goes to /dev/null, the empty output reads as "not there", and the agent reports repositories lost that a sibling session had moved there on the owner's instruction
- looks like: `ls -l ~/.Trash 2>/dev/null` prints `total 0` and the report says the missing repositories are in no archive and not in the Trash
- tell: the same listing without the redirect says "Operation not permitted"; `[ -d <exact path> ]` finds the directory
- do instead: thea shell refuses a listing or search of the Trash whose stderr is discarded; probe an exact path with `[ -d ]` or ask the session that moved it. A recursive delete of a repository-level directory is refused too, so a removed repository is always a move into ~/Projects/_archives or the Trash, and absence is never inferred from a listing

## a_screenshot_for_layout_check

- shape: an agent answers a layout question (does it overflow, is it aligned, did the element render) by taking a screenshot and judging it by eye, when the DOM states the same fact as a number. The image is not a check: it renders the page into context, stays there for the rest of the session, and is retaken after every edit, so the cost compounds per iteration while the verdict stays a judgement. Distinct from a_check_satisfied_by_a_rendering, where a passing check is wrong; here the check is right and paid for in the wrong unit
- looks like: Agent takes screenshots to check UI layout; each image stays in context and burns tokens
- tell: a session transcript with several full-scale screenshots of one page between edits, and no read_page, get_page_text or javascript_tool call measuring scrollWidth, a bounding rect or a computed style
- do instead: measure before looking: read the accessibility tree or page text, and settle layout with JavaScript (scrollWidth against clientWidth, getBoundingClientRect, getComputedStyle). An image only for a visual judgement no number can make, at most two per task, scale 0.4 or below, at the end. Enforced by a host PreToolUse hook on both browser computer tools and both browser_batch tools, matching the screenshot and zoom actions (the act, not the tool name): silent for two images per session, a warning to the agent at three and four, refused past four unless every image in the call is scale 0.4 or below; its suite plants 14 cases and kills 12 of 12 mutants

## a_contract_generalized_from_one_instance

- shape: a document states a contract for every member of a family (every lane repo has a status script with exit codes 0/1/2) after reading one member, and the other members were never opened
- looks like: a tidy table whose header reads as fact, written from one README
- tell: running the claimed contract in each member finds it in one; the others have no such script
- do instead: before a claim covers a family, run or list the claimed thing in every member and write the count (1 of 4), never the family

## an_env_secret_passed_as_argument

- shape: a process launcher receives a secret assignment as an argument, making the credential visible to process inspection even though the called tool reads it from the environment
- looks like: a bounded diagnostic appears safe because its subprocess has the intended environment, while a process listing reveals the credential in the launcher arguments
- tell: the command line contains NAME=value for a credential-bearing name; correct inheritance has no secret value in argv
- do instead: export named secrets into the shell environment before launching a subprocess, and pass only the command and non-secret arguments through wrappers
