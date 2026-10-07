# Proven moves

GENERATED from atlas.yaml/agent_success_patterns.

## ship_user_actions_as_user_only_skills

- move: ship an action a person triggers by name as a skill marked disable-model-invocation, never as a file in a directory the runtime loads whole
- when: a plugin gains a slash command, agent or output style, or a directory a runtime scans gains a scope
- verify: plant a commands scope: the plugin probe refuses it; run the lane skill: its script flag still answers
- answers: a_generated_page_loaded_as_a_component

## gate_on_the_unpiped_exit_code

- move: run the gate unpiped, or under `set -o pipefail`, and branch on its own exit code; read long output from the log
- when: any check, test or build whose result decides a commit, push, merge or close
- verify: `thea shell "<cmd>"` exits 0, and the step after the gate names the code it read
- answers: a_verdict_printed_and_not_gated

## route_every_read_through_its_owner

- move: give one input one owning reader, route every caller through it, then declare the call as that row's sole_reader so a new private copy fails the contract
- when: a second caller starts reading an input another module already reads — a listing, a source tree, a config dialect
- verify: plant the raw call back into one caller: `atlas.py check` fails naming the file and the owning function
- answers: a_reader_written_once_per_caller

## resolve_every_scheduled_target_on_its_host

- move: sweep every scheduler on the host that runs it — hooks, timers, cron, agent job lists — resolve each script, program, working directory and changed-into path, and fail on a missing one, a path from another platform, or a wrapper that exits zero on a missing target; a paused job warns, an empty roster fails
- when: deleting or moving a script or repository, copying jobs to another host, and on every scheduled health run
- verify: the sweep prints its job and target counts, goes red on a planted missing target, and is clean on the real hosts
- answers: a_hook_that_runs_a_deleted_script

## judge_the_payload_not_the_status

- move: judge an answer by the fields it must carry; a 200 or an exit 0 with an empty payload is unanswered, and a zero or false stays a value
- when: reading any API, model or tool result that will be scored or acted on
- verify: the answer path runs through one predicate naming its required fields
- answers: a_success_rendering_read_as_an_answer, a_non_answer_scored_as_wrong

## drive_it_before_calling_it_working

- move: report a capability as working only after one real request went through it end to end; a roster entry, a health 200 or a registered bridge is reported as PREREQUISITE SATISFIED
- when: wiring a model, a lane, a bridge or a tool, and reporting whether it now works
- verify: the report names the request that was driven through and the answer it returned; every unchecked condition is listed as unproven
- answers: a_prerequisite_reported_as_the_capability

## probe_the_capability_after_every_change

- move: after any update, rebuild or configuration change to a tool or a model, drive one real task through it and check the output before the change counts as landed
- when: a self-update, a package upgrade, a model rebuild or a serving-configuration change
- verify: the change log holds a passing capability probe of the same subject, newer than the change; a presence or version probe is named as not counting
- answers: a_self_update_that_leaves_a_placeholder_binary, a_model_config_change_without_an_eval, a_model_rebuild_that_drops_the_chat_template

## count_the_claimants_before_trusting_the_queue

- move: count running instances of each declared singleton by command line before trusting its queue, and stop the second claimant rather than restarting the first
- when: a control plane, a scheduler or any daemon that claims work, whenever it can be started from more than one surface
- verify: the singleton check reports one instance per declared singleton, and a second copy started by hand is refused or attached
- answers: a_second_claimant_of_a_singleton

## generate_then_stage_again

- move: generate every count, list and link from its declaration and never type one; stage, `thea check --fix`, stage again
- when: a change that touches a declaration, a tracked file set or a document carrying a generated block
- verify: `thea check` exits 0 on the staged tree, and `thea index` shows no drift
- answers: a_count_typed_into_prose, a_generated_block_whose_input_is_the_index, a_generated_block_carrying_a_relative_link, a_second_declaration_of_one_value, a_derived_roster_written_out_by_hand

## read_the_tree_you_act_on

- move: list files with git (the tracked set), never the directory on disk, and resolve the repository a command acts on from the caller, never from the tool
- when: a generator, a sweep, a landing or a check run from another repository
- verify: the command run from a scratch repository names only that repository's files
- answers: a_generator_that_reads_the_disk_not_the_tree, an_agent_landing_that_targets_the_atlas

## prove_on_every_correct_shape_first

- move: before a check refuses anything, run it over a correct example of every shape it claims — dialect, revision, path form, shebang — and state what it does not measure
- when: writing or widening a guard, a validator or a compatibility claim
- verify: `python scripts/enforce.py measure` refuses no correct example, and the instrument prints its scope
- answers: a_check_proven_on_one_shape_of_input, an_instrument_wrong_in_its_scope, a_blanket_rule_over_unlike_things

## plant_a_defect_that_differs

- move: plant a defect whose text differs from the original and assert the refusal by its message, never by a literal that later moves
- when: adding a test for a guard
- verify: the plant is refused when it equals the original, and the case asserts a message
- answers: a_fixture_that_names_what_it_could_read

## count_and_refuse_zero

- move: print every roster's count and refuse a zero — no targets, no files and no cases are findings, not passes
- when: any glob, list or query a build, scan or campaign iterates
- verify: the run prints `N of M` and exits non-zero on 0
- answers: a_roster_that_resolved_to_nothing, a_gate_that_resolves_to_silence

## parse_first_then_judge

- move: parse every input once, report malformed input as a finding and let every other guard continue; generate YAML values with `safeedit.py quote`, never quote by hand
- when: a checker reading input another checker validates, or any hand edit to YAML
- verify: `thea check` reports the parse error and every other finding in one run
- answers: a_guard_that_crashes_on_another_guards_input, a_flow_value_split_on_a_comma

## adjudicate_every_argument

- move: hand every path a command carries to the same path verdict as its binary, including `--option=value` forms
- when: allowing a binary to an agent, or adding one to an allowance
- verify: `agentpolicy.argument_verdict` refuses a forbidden path passed as an argument
- answers: an_allowed_binary_whose_argument_nothing_adjudicated

## messages_through_a_quoted_heredoc

- move: write every commit message and pull request body through a quoted heredoc (`<<'EOF'`) or `-F <file>`
- when: any commit, tag or body containing backticks, `$` or more than one line
- verify: `thea shell "<cmd>"` exits 0, and `git log -1` shows the message whole
- answers: a_backtick_inside_a_double_quoted_shell_string

## land_in_one_step_close_on_content

- move: land with `branchstate.py --land` — pull, rebase, push, open and arm the merge together — and close or delete a branch only after `thea landed` exits 0
- when: finishing a lane, closing a pull request or deleting a branch
- verify: `thea landed <branch>` exits 0, or the pull request shows auto-merge armed
- answers: a_pushed_lane_nothing_will_merge, a_branch_judged_landed_by_its_file_list, a_rebase_that_runs_before_a_push_that_will_be_refused, a_lane_on_a_replaced_history

## wait_on_a_pid_not_a_pattern

- move: wait on the harness's background-task notification or a PID; if a pattern is unavoidable, bracket its first character (`[s]leep`) so it cannot match the shell running it
- when: any wait, poll or kill that selects processes
- verify: `thea shell "<cmd>"` exits 0
- answers: a_wait_that_matches_itself

## print_a_literal_through_printf

- move: print any literal that can begin with a dash through `printf '%s\n'` or `print -r --`, and open one generated file after changing its generator
- when: a script that writes a fence, a flag-looking value or user text
- verify: the generated file's first line is the literal, and `thea shell` exits 0
- answers: a_leading_dash_argument_read_as_an_option

## ignore_instead_of_untracking

- move: stop a path mattering with .gitignore while it stays tracked; untrack a directory only once every clone holds a copy outside the repository
- when: a tracked directory that should no longer change in git
- verify: `git status` on a second clone after its pull still shows the files
- answers: an_untrack_that_deletes_on_every_other_clone

## pull_by_rebase_abort_on_conflict

- move: pull with `--rebase --autostash` (or `--ff-only`); on a conflict abort and name the files, so the tree is exactly as it was
- when: any pull, above all one a hook or a schedule runs unattended
- verify: `git diff --name-only --diff-filter=U` prints nothing after the pull
- answers: a_pull_that_leaves_a_half_merge

## match_the_act_not_the_tool

- move: key a guard on the ACT — the path about to be written, the commit about to be made — read from every tool's input, the shell's included
- when: writing any pre-action hook or policy check
- verify: the guard fires when the same act arrives through a shell heredoc
- answers: a_guard_matched_on_the_tool_name_rather_than_the_act

## plan_the_cut_from_the_named_parts

- move: when a cap fails, read the largest parts the breach names, plan the whole cut against every cap once, then build
- when: any size, byte or line cap that fails
- verify: one edit brings every cap under, measured before and after
- answers: a_turn_spent_rewording_instead_of_building

## audit_read_only

- move: run an audit with THEA_READ_ONLY=1 and never beside an editor; a suite that plants and restores holds the worktree lock
- when: any review, audit or measurement run while someone else edits
- verify: the suite refuses to start under THEA_READ_ONLY=1
- answers: a_read_only_audit_that_ran_a_mutating_suite

## read_the_authority_not_the_cache

- move: name the cache a reading comes from and read its authority — the API, git, the file — before acting on a page or a status
- when: acting on a status page, a badge, a dashboard or a remembered number
- verify: the step cites the authority it read and when
- answers: a_cached_reading_read_as_a_measurement

## silence_is_a_third_state

- move: give every probe three outcomes — answered yes, answered no, did not answer — and let only an answer move a verdict
- when: a probe, health check or classifier decides whether something is down, broken, empty or absent
- verify: a run with the network cut prunes, retires and fails nothing; it reports a blackout
- answers: a_silence_read_as_a_verdict

## credentials_by_name_never_by_value

- move: refer to a credential by its variable name and load it from the keys file; never write the value into a command, a file or a handed-over block
- when: setting up, testing or rotating any key, token or password
- verify: the command text contains no credential prefix; `thea shell` allows it
- answers: a_credential_typed_into_a_command

## read_every_quoted_anchor_before_the_suite

- move: check every string a test quotes from another file against that file statically, before any planted suite runs
- when: editing a document or source file that tests quote, or adding a test that locates text by quoting it
- verify: `python scripts/plantcheck.py` reports zero findings over all anchors
- answers: a_quote_that_outlived_its_text

## diverge_before_converging

- move: write the choice as a brainstorm record — three options with a do_nothing baseline, axes, pre-mortems, kill signals — and converge only on an undominated option
- when: a strategic or architectural choice, a new route or agent, anything irreversible or expensive to undo
- verify: `thea brainstorm <record>` exits 0
- answers: a_first_idea_argued_as_the_only_option

## splice_new_objects_as_text

- move: insert new keys into a hand-formatted config as TEXT at a known anchor and read the file back; never reserialise the whole file
- when: adding entries to a JSON, JSONC, YAML or TOML file someone formats by hand
- verify: the diff shows only the added lines, and the file still parses
- answers: a_round_trip_that_drops_what_the_format_allowed

## run_a_script_by_its_shebang

- move: run a script as ./x or by the interpreter its first line names, never by its suffix; an rc of 2 from a wrong interpreter is NOT RUN, not FAIL
- when: invoking any test or guard script whose interpreter is not obvious from its name
- verify: the interpreter in the command equals the one on line 1 of the script
- answers: a_suffix_read_as_the_interpreter

## ahead_zero_means_sweep

- move: when a lane reads ahead=0 against its base, remove its worktree, branch and tags in the same step
- when: after a lane lands or is found already merged
- verify: worktree list and branch list no longer name the lane
- answers: a_finished_worker_leaves_its_resources_running

## scope_a_refusal_to_its_pipeline

- move: judge a shell refusal against the one pipeline it concerns, never the whole command line
- when: a hook or gate refuses a compound command
- verify: a planted command whose refused shape sits in a different statement passes
- answers: a_check_proven_on_one_shape_of_input

## generate_every_quoted_value

- move: print every quoted value with the format's own emitter — `safeedit.py quote` for a scalar, `safeedit.py entry` for a whole ledger entry — never type the quotes
- when: adding or editing any YAML value, ledger entry or config scalar that holds prose
- verify: the entry reads back equal to its fields, which safeedit.add_entry refuses otherwise, and `atlas.py check` exits 0
- answers: a_value_quoted_by_hand

## declare_a_surface_before_loading_it

- move: declare each connector, plugin, MCP server or skill in an allowlist with why it loads and its CLI equivalent, before enabling it
- when: adding any tool surface to an agent
- verify: the surface bound check passes with the new entry, and the loaded count equals the declared count
- answers: an_unallowlisted_tool_surface_that_grows

## sweep_only_what_regenerates

- move: sweep a cache only after proving its owner regenerates every target; anything installed or authored is moved, never deleted
- when: purging any cache, tool store or temporary tree
- verify: the sweep check refuses a planted source file in the target, and the purged tools still run after
- answers: a_cache_sweep_that_deletes_a_source_file

## wait_on_a_shared_lock_under_one_deadline

- move: retry a shared lock every time it frees, under one deadline for the whole wait, never a fixed retry count
- when: a step refuses NOT RUN because a sibling process holds a machine-wide lock
- verify: fake two lost races then a pass: land returns 0 after three attempts; a single-retry mutant returns 75
- answers: a_shared_lock_retried_once_against_siblings

## read_the_one_line_that_states_a_value

- move: anchor a freshness check on the one line that states the value, never on any rendering of it in the file
- when: a check verifies a version, count or path is current inside a file that also carries generated copies of it
- verify: a shallow clone or a stale navigation line is refused although a generated table in the same file carries the new value
- answers: a_check_satisfied_by_a_rendering

## put_a_worktree_beside_its_repo

- move: create every worktree beside its repository as <repo>-wt/<name>, and read a tree's files through files_under, which stops at any directory holding its own .git
- when: a lane, a testbed or a session needs a second checkout, or a new reader walks a tree from its root
- verify: plant a nested worktree holding a network import: network_modules still lists only the tree's own leak, in git and outside it
- answers: a_worktree_inside_the_tree_it_copies

## run_the_repo_by_its_declared_interpreter

- move: run a repository's scripts through the interpreter its manifest declares (`uv run python scripts/<x>.py`, or the installed launcher), never a bare `python3` whose version PATH decides
- when: invoking any Python script, test or contract check in a repository whose pyproject.toml declares requires-python
- verify: `uv run python scripts/atlas.py doctor` exits 0, and a bare-interpreter run below the floor exits 2 with NOT RUN instead of a traceback
- answers: an_interpreter_below_the_declared_floor
