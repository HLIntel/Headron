#!/usr/bin/env python3
"""Mutation tests for the contract harness.

WHY: `atlas.py check` is the only thing standing between this repository and
silent drift, and until now nothing tested IT. A guard that is never mutation-
tested is decoration: when it works it prints nothing, and so does a broken one.

Every case below names the WRONG IMPLEMENTATION it kills, and each one plants a
real defect on disk, runs the real check, and restores the file. The case COUNT
is asserted at the end, because a harness can print "all pass" over cases that
never ran.

    python scripts/atlas_test.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agentpolicy
import atlas
import atlasgen
import atlasinv
import packmanifest
import safeedit

_VERSION = (ROOT / "VERSION").read_text().strip()  # the ONE declaration; never typed into a fixture

CASES: list[tuple[str, str]] = []


def run_check() -> tuple[int, str]:
    atlas.atlas.cache_clear()
    packmanifest.reset_caches()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = atlas.check()
    return rc, buf.getvalue()


def case(name: str, kills: str, expect_fail: bool, needle: str | None = None) -> None:
    rc, out = run_check()
    failed = rc != 0
    if failed != expect_fail:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  rc={rc}, expected {'non-zero' if expect_fail else '0'}\n{out[:800]}")
    if needle and needle not in out:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  expected {needle!r} in output\n{out[:800]}")
    CASES.append((name, kills))
    print(f"  ok    {name}")


def suite_lock(wait: float | None = None):
    """One mutating suite per worktree. The file descriptor IS the lock; closing it releases.

    Two suites interleave their plant/restore windows exactly as an editor does, and each restores
    bytes the other planted — the same lost update, with nobody at a keyboard to notice.
    """
    import fcntl
    where = subprocess.check_output(["git", "rev-parse", "--git-path", "atlas-test.lock"],
                                    cwd=ROOT, timeout=600).decode().strip()
    handle = open(ROOT / where if not Path(where).is_absolute() else where, "w")  # noqa: SIM115
    from resilience import wait_until

    def acquired() -> bool:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True
    # WAIT ON THE CONDITION, bounded: a short overlap with a measurement clears by itself; a long
    # one still fails loudly rather than interleaving planted defects with a reader.
    # `wait=0` is ONE attempt: the self-test asserting refusal paid the full 120 s ceiling on every
    # run (MEASURED 120.0 of 176.2 s wall, 2.28.0) to learn what the first attempt already said.
    ceiling = float(os.environ.get("ATLAS_LOCK_WAIT", "120")) if wait is None else wait
    if not wait_until(acquired, timeout=ceiling, interval=2.0):
        handle.close()
        raise SystemExit("another atlas_test run or measurement holds this worktree — REFUSING to "
                         "interleave planted defects with it")
    return handle


@contextlib.contextmanager
def mutated(rel: str, transform):
    """Plant a defect in a tracked file, then restore it byte for byte."""
    path = ROOT / rel
    backup = path.read_bytes()
    try:
        planted = transform(backup.decode("utf-8"))
        # A MUTATION THAT DID NOT MUTATE. str.replace with no match returns the
        # string unchanged and says nothing, so the case then "passes" against a
        # pristine file — a green harness over a defect that was never planted.
        if planted == backup.decode("utf-8"):
            raise SystemExit(f"MUTATION DID NOT APPLY to {rel}: the pattern no longer matches this file")
        # JOURNAL BEFORE PLANTING (3.13.0): a killed run never reaches `finally`, so the tree must
        # carry what it takes to undo this — atlas.py check refuses a leftover, --restore reverts it.
        journal = safeedit.plant_journal()
        journal.mkdir(parents=True, exist_ok=True)
        entry = journal / rel.replace("/", "%2F")
        entry.with_suffix(entry.suffix + ".backup").write_bytes(backup)
        entry.with_suffix(entry.suffix + ".planted").write_text(planted, encoding="utf-8")
        path.write_text(planted, encoding="utf-8")
        yield
    finally:
        # THE RESTORE MUST NOT ERASE A WRITE IT DID NOT MAKE. MEASURED at 2.27.0: an agent edited
        # atlas.yaml while this suite ran in the background; the restore wrote back the bytes it had
        # saved BEFORE that edit, and the edit vanished with no error. If the file is no longer what
        # was planted, somebody else wrote it: their version is KEPT beside it and the run fails.
        # NARROWED ON FIRST CONTACT, per the rule that a guard firing on correct code gets
        # switched off: the "index --write repairs the drift" case REWRITES the file inside this
        # block on purpose, returning it to the original. Planted or original is this test's own
        # business; any THIRD state is a writer this test did not make.
        current = path.read_bytes()
        if current not in (planted.encode("utf-8"), backup):
            kept = path.with_name(f"{path.name}.concurrent-{os.getpid()}")
            kept.write_bytes(current)
            path.write_bytes(backup)
            for leftover in safeedit.plant_journal().glob(rel.replace("/", "%2F") + ".*"):
                leftover.unlink()
            raise SystemExit(f"CONCURRENT WRITE to {rel} while a defect was planted — the other "
                             f"writer's version is kept at {kept.relative_to(ROOT)}; nothing was "
                             "erased. Never edit the tree while this suite runs.")
        path.write_bytes(backup)
        for leftover in safeedit.plant_journal().glob(rel.replace("/", "%2F") + ".*"):
            leftover.unlink()
        atlas.atlas.cache_clear()
        packmanifest.reset_caches()


def property_sweep() -> None:
    """4,000 seeded inputs over the router and the entry grammar.

    Its own function because `astshape.py` reported main() over the line cap — the same
    ratchet that split atlas.py check(), firing on the test harness this time.
    """
    # 7b. PROPERTY SWEEP over the router and the manifest grammar (2.2.0).
    #     Not a fuzzer integration — Scorecard looks for OSS-Fuzz or ClusterFuzzLite and will not
    #     detect this, which docs/CERTIFICATION.md says plainly. It is the proportionate instrument
    #     for a local CLI: a seeded generator, so a failure is reproducible from the seed alone,
    #     and NO new dependency, so it runs everywhere the contract runs.
    import random as _random
    import string as _string

    import packmanifest as _pm

    rng = _random.Random(20260924)
    alphabet = _string.ascii_letters + _string.digits + "._-|/ ()+:*?\\\t"
    sweep = 0
    for _ in range(4000):
        candidate = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 24)))
        route = atlas.route_for(candidate)            # must never raise, whatever it is handed
        assert route is None or route in atlas.route_targets(), f"invented a route for {candidate!r}"
        kind = _pm.entry_kind(candidate)
        assert kind in {"command", "lib", "builtin", "concept", "none", "invalid"}, kind
        binaries = _pm.entry_binaries(candidate)
        assert (kind == "command") == bool(binaries), f"{candidate!r}: kind {kind} against {binaries}"
        assert all(" " not in b for b in binaries), f"{candidate!r} produced a binary with a space"
        assert kind != "invalid" or not _pm.manifest_pattern("entry").fullmatch(candidate), \
            f"{candidate!r} is invalid yet the grammar accepts it"
        if _pm.manifest_pattern("entry").fullmatch(candidate):
            # Anything the grammar ACCEPTS must be classifiable and, if a command, runnable-shaped.
            assert kind != "none" or candidate == "none", candidate
            assert not (kind == "command" and ("(" in candidate.split(" ", 1)[0])), candidate
        sweep += 1
    assert sweep == 4000, sweep
    CASES.append(("property sweep: 4000 generated inputs over the router and the entry grammar",
                  "a router that raises on a hostile path, and a grammar that accepts what nothing "
                  "can classify"))
    print("  ok    property sweep: 4000 seeded inputs, router and entry grammar total")


def promoted_invariant_cases() -> None:
    """One planted defect per invariant that was promoted from DECLARED to ENFORCED.

    Its own function because the structure gate refused main() at 241 against a cap of 239 —
    the same gate, on the test harness, for the second time. Each row is (file, find, replace,
    invariant, the defect it kills).
    """
    # 8b. EVERY PROMOTED INVARIANT, ONE PLANTED DEFECT EACH (1.1.0).
    # A check that cannot fail is worse than a declaration: it reads as coverage.
    # Each row is (file, find, replace, invariant name, the defect it kills).
    promoted = [
        (".github/workflows/atlas-ci.yml", "    timeout-minutes: 10", "    # no timeout",
         "explicit_deadlines", "a CI job that hangs until GitHub kills it"),
        (".github/CODEOWNERS", "* @HeartlandIntel", "# no default owner",
         "auditable_changes", "new paths landing with no reviewer"),
        (".github/pull_request_template.md", "## Verification", "## Vibes",
         "goal_acceptance_is_explicit", "a PR that never states what would prove the goal met"),
        # Indent the changelog LINE: the version string still appears in the file, so
        # the version-sync check stays satisfied and only this invariant can fire.
        #
        # THE VERSION IS DERIVED, NEVER TYPED. This fixture read "1.1.0" literally, so the moment
        # VERSION was bumped to 1.2.0 the mutation indented a line the check no longer looks at:
        # the case went green while planting nothing, and a silently-passing mutation test is worth
        # less than no test, because it is believed. One number, one declaration — VERSION owns it.
        ("docs/VERSIONING.md", f"\n{_VERSION} ", f"\n {_VERSION} ",
         "rollback_high_impact", "a released version with no changelog line to revert to"),
        ("languages/python/tools.yaml", "  avoid_by_default:\n  - duplicate_linters\n  - unbounded_async_tasks", "  avoid_by_default: []",
         "tool_surfaces_are_bounded", "a manifest that names nothing to avoid, so the surface is everything"),
        (".vscode/mcp.json.example", '"semgrep": {', '"exfiltrator": {',
         "mcp_is_task_scoped", "shipping an MCP server no published profile names"),
        # The word appears twice; replacing one leaves the check satisfied, which is
        # itself the lesson — a single-occurrence mutation proves nothing about a
        # check that greps. Replace BOTH.
        ("patterns/BOUNDARY-BREAKAGE.md", "timeout", "deadline",
         "production_boundaries_are_contracts", "a boundary doc that never mentions timeouts", -1),
        ("config/github-labels.json", '"namespaces"', '"namespaces"  ,,',
         "schema_first", "a machine-read file that no longer parses"),
    ]
    for row in promoted:
        rel_path, find, repl, invariant, kills = row[:5]
        count = row[5] if len(row) > 5 else 1
        with mutated(rel_path, lambda s, f=find, r=repl, c=count: s.replace(f, r, c) if c > 0 else s.replace(f, r)):
            case(f"{invariant} FAILS when its property is broken", kills, True, invariant)


def agent_and_entry_cases() -> None:
    """One planted defect per rule added with the agent controls and the entry-cost ratchet.

    Its own function because the structure gate refused main() at 244 against a cap of 232 — the
    third time that gate has fired on this harness, and the answer is the same every time: split
    the function, never raise the number that caught it.
    """
    # 10. THE AGENT CONTROLS (2.9.0) — the autonomous profile was a label for eight minor versions.
    #     Each mutation below is the exact shape that makes a declared control read as an enforced
    #     one: an enforcer that does not resolve, a gate nothing runs, an authority claimed twice,
    #     a modifier pointing at no class, and a reference contract that no longer conforms.
    with mutated("atlas.yaml", lambda s: s.replace(
            "enforced_by: agentpolicy.command_verdict", "enforced_by: agentpolicy.command_verdicts", 1)):
        case("a control whose enforcer does not resolve FAILS", "five controls named in a task profile and "
             "enforced by nothing, which an agent is bound by only if it chooses to read them", True,
             "does not resolve to a callable")
    with mutated("atlas.yaml", lambda s: s.replace("  unit_tests: {role: test, per_file_runners:", "  unit_tests: {role: none, per_file_runners:", 1)):
        case("a gate that resolves to no tool and names no closer FAILS", "a gate satisfied by an agent "
             "saying it was, because nothing joined the word to a command", True, "reads as one that passed")
    with mutated("atlas.yaml", lambda s: s.replace("    roles: [security]", "    roles: [security, formatter]", 1)):
        case("one authority role claimed by two classes FAILS", "a compiler treated as authority for "
             "behaviour because nothing said what each tool is authoritative FOR", True, "two authorities for one tool")
    with mutated("atlas.yaml", lambda s: s.replace(
            "  additive_endpoint:\n    applies_to: api_change", "  additive_endpoint:\n    applies_to: api_changes", 1)):
        case("a risk modifier applying to no change class FAILS", "a modifier that adds gates to a class "
             "that does not exist, so selecting it changes nothing and reads as extra rigour", True,
             "is not a change class")
    # A SECOND DECLARATION OF THE VERSION. Five bumps went past the reference contract's
    # atlas_version, every local gate passed, and CI refused the whole task as a stale plan.
    with mutated("tools/agent-task.example.json",
                 lambda s: s.replace(f'"atlas_version": "{_VERSION}"', '"atlas_version": "0.0.1"', 1)):
        case("a reference contract pinned to another contract version FAILS", "a version site "
             "outside the roster that asserts them, found by CI after every local gate passed",
             True, "cannot pass its own CI step")
    with mutated("tools/agent-task.example.json", lambda s: s.replace('"schema": 1', '"schema": 2', 1)):
        case("a reference contract that no longer conforms FAILS", "the one worked example of the task "
             "contract drifting away from the schema that defines it", True, "reference contract")

    # 10b. THE ENTRY COST (2.10.0) — a repository is a blob because of what it hands over
    #      unasked, not because of what it contains. Both directions of the band are planted.
    # THE ANCHORS ARE READ, NEVER TYPED. Two of these named a literal budget and a literal file
    # list; both moved when the instrument's SCOPE was corrected, and the harness refused rather
    # than planting nothing — which is the behaviour, and also the second time a fixture in this
    # file has named a value it could have read. atlas.yaml owns the number.
    _agent_budget = re.search(r"^      budget_bytes: (\d+)$", (ROOT / "atlas.yaml").read_text(), re.M).group(0)
    _first_entry = re.search(r"^      alternatives: \[([A-Za-z0-9._]+)", (ROOT / "atlas.yaml").read_text(), re.M).group(1)
    with mutated("atlas.yaml", lambda s, a=_agent_budget: s.replace(a, "      budget_bytes: 900", 1)):
        case("an entry path over its budget FAILS", "an entry document growing a page at a time while "
             "every other count in the contract stays green", True, "the ratchet only falls")
    with mutated("atlas.yaml", lambda s, a=_agent_budget: s.replace(a, "      budget_bytes: 999000", 1)):
        case("a budget raised to make room FAILS", "a ceiling nobody is near, which absorbs the next "
             "addition instead of refusing it", True, "slack")
    with mutated("atlas.yaml", lambda s, f=_first_entry: s.replace(f"alternatives: [{f}", "alternatives: [gone-x.md", 1)):
        case("an entry path naming a missing file FAILS", "a measured entry cost that silently stopped "
             "counting one of the documents it is measuring", True, "does not exist")


def external_api_cases() -> None:
    """The frozen machine output, and the two rosters a consumer would find broken first.

    Its own function for the fourth time the shape gate refused main(). The rule is now
    written into the generated entry point: add a rule, add its planted defect, and give
    the fixture its own *_cases() rather than growing the one that caught you.
    """
    # 13. BOUNDED AUTONOMY AND THE FENCE (2.21.0).
    with mutated("atlas.yaml", lambda s: s.replace(
            "    on_breach: refuse, and say which control refused",
            "    on_breach: log it and carry on", 1)):
        case("a hard tier that does not refuse FAILS", "a perimeter that reasons at its edge, "
             "which makes it the middle tier wearing the outer tier's name", True,
             "does not REFUSE at its edge")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    here: [every ratchet — entry_paths, install_footprint, code_shape, example_coverage — the tool",
            "    here: [the tool", 1)):
        case("a ratchet named by no tier FAILS", "an untiered bound, which every reader gets to "
             "classify generously about their own change", True, "untiered bound")
    with mutated("docs/VERIFY.md", lambda s: s.replace("```", "``", 1)):
        case("an unclosed code fence FAILS", "a page that stops working halfway down while every "
             "other check passes over it", True, "never closes")

    # 12. THE HOST AND THE PARSERS (2.19.0). Both were earned: two host configs in this tree did
    #     not parse at all, and the first version of the host guard fired on `git status`.
    with mutated(".zed/tasks.json", lambda s: s.replace(
            '"check"\n', '"check", "&& rm -rf /tmp/x"\n', 1)):
        case("shell logic in a host config FAILS", "behaviour that exists only inside one editor, "
             "reachable by no terminal and no CI, whose absence is silent", True,
             "exists nowhere a terminal or CI can reach it")
    with mutated(".vscode/tasks.json", lambda s: s.replace('"${file}"', '"\\${file}"', 1)):
        case("a tracked JSON that does not parse FAILS", "a configuration file that silently does "
             "nothing while every document check passes over it", True, "is not valid JSON")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    enforced_by: atlascore.StrictLoader, which refuses a duplicate rather than resolving it",
            "    enforced_by: ''", 1)):
        case("a parser rule with no enforcer FAILS", "a table of parser advice that reads as "
             "protection while enforcing nothing", True, "missing enforced_by")

    # 11. THE EXTERNAL API (2.11.0) — a consumer depends on these records, so they are asserted
    #     against the frozen schema, not against whatever the producer happened to emit today.
    _out = json.loads((ROOT / "tools/atlas-output.schema.json").read_text())
    _records = [atlas.route_record("scripts/atlas.py"), atlas.route_record("Makefile"),
                atlas.plan_record("scripts/atlas.py", "python", "implementation", "source_change", []),
                atlas.plan_record("scripts/atlas.py", "python", "default", None, None)]
    _records += [agentpolicy.process_record(p) for p in atlas.atlas()["processes"]]
    # all three gate states, so the frozen shape is proven for each and not only the happy one
    import io as _io
    _buf = _io.StringIO()
    with contextlib.redirect_stdout(_buf):
        atlas.main(["decide", "caching_strategies", "--json"])
    _records.append(json.loads(_buf.getvalue()))
    _records += [atlas.gate_record("scripts/atlas.py", "unit_tests"),
                 atlas.gate_record("languages/bqn/OPERATING.md", "unit_tests"),
                 atlas.gate_record("Makefile", "unit_tests")]
    try:  # THE REFERENCE IMPLEMENTATION, over EVERY record — not only the manifests it once covered
        from jsonschema import Draft202012Validator as _Ref
        _reference = _Ref(_out)
    except ImportError:
        _reference = None
    for _record in _records:
        _bad = packmanifest.validate(_record, _out, str(_record["command"]))
        assert not _bad, f"{_record['command']} record violates the frozen output schema: {_bad[:2]}"
        if _reference is not None:
            _ref_bad = [e.message for e in _reference.iter_errors(_record)]
            assert not _ref_bad, (f"{_record['command']}: this validator accepts what the JSON Schema "
                                  f"reference refuses — the two disagree: {_ref_bad[:1]}")
    assert len(_records) == 8 + len(atlas.atlas()["processes"]), "the record sweep shrank"
    assert [r["state"] for r in _records[-3:]] == ["runnable", "absent", "undeclared"], \
        f"gate records did not cover all three states: {[r['state'] for r in _records[-3:]]}"
    CASES.append((f"all {len(_records)} machine records satisfy the frozen output schema",
                  "an external API that is whatever the producer emitted today"))
    print(f"  ok    {len(_records)} machine records validate against tools/atlas-output.schema.json")

    with mutated("pyproject.toml", lambda s: s.replace('py-modules = ["atlas_cli"]', 'py-modules = ["atlas_cli", "atlas"]', 1)):
        case("a harness module shipped in the wheel FAILS", "a second copy of the harness, pinned by pip "
             "rather than by the atlas it runs against, one version apart and missing what check imports",
             True, "a harness module in the wheel")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    stop_when: [gate_refused, scope_expanded, budget_exhausted]",
            "    stop_when: []", 1)):
        case("a process with no stopping condition FAILS", "a process that expands until something "
             "else notices, which is what the agent controls were built for", True, "declares no stop_when")


def route_ambiguity_cases() -> None:
    """Every declared precedence rule, and the paths that are ambiguous for a reason.

    THE DUPLICATE-KEY GUARD ONLY COVERS ONE KIND OF AMBIGUITY. It refuses two YAML keys claiming
    one extension; it says nothing about a file that matches an extension AND sits inside another
    pack, about a symlink, about a path that traverses back inside, or about the four precedence
    rules this router does not resolve at all. Each row below is one of those, asserted as
    BEHAVIOUR, so a future change to the precedence order shows up here rather than in a consumer.
    """
    declared = [str(p) for p in atlas.atlas()["routing_policy"]["precedence"]]
    record = atlas.route_record("scripts/atlas.py")
    assert [row["rule"] for row in record["precedence"]] == declared, \
        "the route record's precedence list must BE atlas.yaml's, in order"
    assert {row["rule"] for row in record["precedence"] if row["resolved_here"]} \
        == set(atlas.PRECEDENCE_IMPLEMENTED), "the record disagrees with what the router implements"
    assert len(set(atlas.PRECEDENCE_IMPLEMENTED)) < len(declared), \
        "if every rule were implemented here, the caller-side list would be empty and unnecessary"

    cases = [
        # (path, expected route, what the wrong implementation would do)
        ("a/b/c.py", "python", "extension routing broken"),
        ("x.PY", "python", "case treated as identity; an uppercase extension is a rendering"),
        ("x.js", "typescript", "a route is a TOOLCHAIN, not a syntax — .js is answered by the ts pack"),
        ("x.fs", "fsharp", "the historical collision: a second '.fs' key moved every F# file to forth"),
        ("x.fth", "forth", "forth keeping its own extensions after the collision was fixed"),
        ("Makefile", None, "a file with no extension inventing a route"),
        (".gitignore", None, "a dotfile whose suffix is empty being read as a suffix"),
        ("README", None, "an extensionless name routing on its stem"),
        ("x.unheard-of", None, "an unknown extension resolving to a generic fallback this router "
                               "does not implement"),
        ("", None, "an empty path"),
        (".", None, "a bare directory reference"),
        ("/tmp/elsewhere/languages/go/x.txt", None, "a path OUTSIDE the repo routing on a matching segment"),
        (str(ROOT / "languages/go/README.md"), "go", "a pack refusing to route to itself"),
        (str(ROOT / "languages/quantum/qsharp/OPERATING.md"), "quantum/qsharp", "a nested pack "
                                                                                "resolving to its parent"),
        (str(ROOT / "languages/README.md"), None, "the pack INDEX resolving as if it were a pack"),
        (str(ROOT / "scripts/../examples/rust/main.rs"), "rust", "a traversal that lands back inside "
                                                                 "the repository being refused"),
    ]
    for path_value, expected, kills in cases:
        got = atlas.route_for(path_value)
        assert got == expected, f"route_for({path_value!r}) == {got!r}, expected {expected!r} — kills: {kills}"

    # A FILE THAT MATCHES BOTH AN EXTENSION AND A PACK DIRECTORY. atlas.yaml puts
    # artifact_extension ABOVE language_directory, so this is decided by declaration rather than by
    # accident — and the evidence line has to SAY which rule won, or the two are indistinguishable.
    inside = str(ROOT / "languages/rust/notes.py")
    route, rule, evidence = atlas.route_with_evidence(inside)
    assert route == "python" and rule == "artifact_extension", \
        f"a .py inside the rust pack resolved {route!r} by {rule!r}; precedence is declared, not guessed"
    assert ".py" in evidence, "the evidence must name what decided it"

    # A SYMLINK IS NOT ITS TARGET for routing: docs/MODEL.md points at MODEL.md and neither has a
    # routed extension, so the honest answer is no route rather than the target's.
    assert (ROOT / "docs/MODEL.md").is_symlink(), "fixture moved: docs/MODEL.md is no longer a symlink"
    assert atlas.route_for("docs/MODEL.md") is None, "a symlinked document invented a route"

    CASES.append((f"route ambiguity matrix: {len(cases)} paths + precedence, symlink and "
                  "extension-over-directory",
                  "a router that looks unambiguous because only one kind of ambiguity was tested"))
    print(f"  ok    route ambiguity matrix: {len(cases)} paths, every precedence rule accounted for")


def knowledge_and_action_cases() -> None:
    """One planted defect per knowledge rule and per pack action.

    Each of these is a declaration that would otherwise be read as covering something. A data class
    with no named failure mode, a fact living in two layers, a dense-only index, an asymmetry with
    nowhere it is applied and an action with no takes_file all LOOK complete.
    """
    with mutated("atlas.yaml", lambda s: s.replace("    chunking: ast_boundaries", "    chunking: fixed_character_count", 1)):
        case("a class chunked by a forbidden method FAILS", "a function split in half, where both "
             "halves retrieve well because similarity cannot tell the unit was broken", True,
             "names as a way never to chunk")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    holds: [the task, the plan, the diff, the last few tool results]",
            "    holds: [the task, the plan, the diff, source files]", 1)):
        case("one fact in two knowledge layers FAILS", "a fact updated in one layer and stale in "
             "the other, with nothing in the output to say which was read", True,
             "a fact in two layers is updated in one of them")
    with mutated("atlas.yaml", lambda s: s.replace(
            "  search: [dense_similarity, sparse_keyword]", "  search: [dense_similarity]", 1)):
        case("a dense-only index FAILS", "an index that cannot find an exact symbol, asked a "
             "question that looks exactly like one it can answer", True, "fewer than two methods")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    applied_at: the task-contract budgets, the audit byte cap, and the refusal to auto-execute",
            "    applied_at: ''", 1)):
        case("an asymmetry with nowhere it is applied FAILS", "an aphorism in a file of rules, "
             "which reads as one of them", True, "aphorism")
    with mutated("atlas.yaml", lambda s: s.replace(
            "  test:    {role: test,                takes_file: false}",
            "  test:    {role: test}", 1)):
        case("a pack action with no takes_file FAILS", "a path appended to a project-wide test "
             "runner, so a green suite is a run of nothing", True, "takes_file")
    with mutated("atlas.yaml", lambda s: s.replace(
            "  format:  {role: formatter,           takes_file: true}",
            "  format:  {role: beautifier,          takes_file: true}", 1)):
        case("a pack action naming no real role FAILS", "an action that resolves to nothing in any "
             "of the 35 manifests and reports it per language instead of once", True,
             "not a manifest authority role")

    with mutated("atlas.yaml", lambda s: s.replace("    packs: [bash]\n", "    packs: []\n", 1)):
        case("a pack in no selection axis FAILS", "a roster that answers what is supported and "
             "never what to use, so the default wins: whatever the author already knows", True,
             "reachable only by already knowing its name")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    when_not: control flow exceeds a screen, or a value needs a type — reach for the workhorse row",
            "    when_not: ''", 1)):
        case("a selection axis with no when_not FAILS", "an axis that recommends itself for "
             "everything, which is how 35 packs become 35 recommendations", True, "recommends itself")
    with mutated("atlas.yaml", lambda s: s.replace("    runtime_dependencies: 1", "    runtime_dependencies: 4", 1)):
        case("a footprint that disagrees with the lock FAILS", "a CLI that drags a dependency tree "
             "behind it, arriving one convenient import at a time", True, "runtime dependency")

    # THE BENCHMARK REPORT IS A RESULT, SO IT IS SCHEMA-CHECKED LIKE ONE. The shape is what makes
    # K, the held-out split and the provenance of each arm structural instead of remembered.
    import bench
    _report = bench.report()
    _rs = json.loads((ROOT / "benchmarks/report.schema.json").read_text())
    _bad = packmanifest.validate(_report, _rs, "benchmark")
    assert not _bad, f"the benchmark report violates its own schema: {_bad[:2]}"
    _measured = [a for a in _report["arms"] if a["obtained_by"] == "instrument"]
    assert _measured, "every arm is a model or not run, so the suite measures nothing"
    _held = _report["tasks"]["held_out"]
    assert _held >= 3, f"{_held} held-out tasks: a suite you select on is in-sample"
    assert _measured[0]["routes_correct_held_out"] == _held, \
        "the held-out set must be reported, and it must pass, or the fixed result is in-sample"
    assert _report["baseline"]["routes_correct_by_chance"] > 0, "a result with no baseline is rhetoric"
    CASES.append((f"benchmark: {_report['tasks']['total']} tasks, {_held} held out, K={_report['k']}, "
                  "baseline printed", "an evidence loop that reports only the arms that flatter it"))
    print(f"  ok    benchmark report validates: {_held} held out, baseline "
          f"{_report['baseline']['routes_correct_by_chance']}")
    with mutated("benchmarks/tasks/route-harness-itself.json",
                 lambda s: s.replace('"expected_route": "python"', '"expected_route": "rust"')):
        bench_rc = bench.main([])
        assert bench_rc != 0, "a benchmark that cannot fail on a wrong route proves nothing"
    CASES.append(("the benchmark FAILS on a wrong route",
                  "a suite whose exit code is zero whatever the router answers"))
    print("  ok    the benchmark fails on a planted wrong route")

    # EVERY PACK ANSWERS THE ACTIONS ITS OWN MANIFEST DECLARES. This is the reverse direction: not
    # "is the table well formed" but "does it resolve against every real pack".
    resolved = unavailable = 0
    for target in atlas.route_targets():
        for action in atlas.atlas()["pack_actions"]:
            argv, _ = agentpolicy.action_command(target, action, "x.txt")
            resolved += bool(argv)
            unavailable += not argv
    assert resolved > unavailable, f"{resolved} actions resolve against {unavailable} that do not"
    CASES.append((f"pack actions resolve {resolved} of {resolved + unavailable} across every pack",
                  "an action table that resolves for the pack it was written beside and for no other"))
    print(f"  ok    pack actions: {resolved}/{resolved + unavailable} resolve across all packs")


def retrieval_cases() -> None:
    """The four things retrieval_change requires, asserted against the index that claims them.

    A declaration named AST chunking, hybrid search, checksum invalidation and a citation rule.
    Each one below is the property, checked on the real index rather than on the sentence.
    """
    import ast as _ast

    import atlasindex

    state = atlasindex.build()
    assert state["chunks"] > 100, f"only {state['chunks']} chunks — the index is not covering the tree"
    assert not state["missing_sidecar_fields"], state["missing_sidecar_fields"]

    # chunk_boundary_test — NO chunk may split a Python definition. The ranges are compared to the
    # AST's own spans, so a length-based splitter sneaking in would be caught by the boundary and
    # not by a reviewer noticing a odd-looking snippet.
    source = (ROOT / "scripts/agentpolicy.py").read_text(encoding="utf-8")
    spans = {(n.lineno, n.end_lineno) for n in _ast.parse(source).body
             if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))}
    indexed = {tuple(r["lines"]) for r in atlasindex.load()
               if r["path"] == "scripts/agentpolicy.py" and r["symbols"] != ["<module preamble>"]}
    assert indexed <= spans, f"a chunk does not align to an AST boundary: {sorted(indexed - spans)[:3]}"
    assert len(indexed) > 10, f"only {len(indexed)} definitions indexed from a file with {len(spans)}"

    # hybrid_recall_check — the two arms must actually disagree, or one of them is decoration.
    by_symbol = [h for h in atlasindex.search("budget_verdict", 5) if h["found_by"] != "cosine"]
    by_cosine = [h for h in atlasindex.search("refuse a command outside the allowance", 5)
                 if h["found_by"] == "cosine"]
    assert by_symbol, "the sparse arm found nothing for an exact symbol it should rank first"
    assert by_cosine, "the dense arm found nothing for a phrase with no matching symbol"
    assert by_symbol[0]["score"] > 1.0, "an exact symbol must outrank a merely topical match"

    # citation_check — an answer whose source cannot be opened is one that cannot be checked.
    for hit in atlasindex.search("sandbox", 5):
        assert (ROOT / hit["path"]).exists() and hit["checksum"] and hit["lines"][0] >= 1, hit

    # freshness — invalidation is by CONTENT, so an edited file must read STALE, not current.
    assert not atlasindex.verify(), "a freshly built index reports itself stale"
    with mutated("scripts/doctor.py", lambda s: s.replace("import", "import  ", 1)):
        assert any("STALE" in p for p in atlasindex.verify()), \
            "an edited file did not invalidate its chunks — the index is answering from old bytes"
    atlasindex.build()

    CASES.append((f"retrieval: {state['chunks']} chunks on declared boundaries, both arms, citations, staleness",
                  "a retrieval policy that describes AST chunking and ships a length-based splitter"))
    print(f"  ok    retrieval: {state['chunks']} chunks, boundaries aligned, both search arms fire, "
          "staleness detected by content")


def jsonschema_cross_check() -> bool:
    """True when an independent validator ran and agreed; False when it is not installed."""
    # 9b. AN INDEPENDENT IMPLEMENTATION, where one is installed. The risk in a hand-written
    #     validator is not being wrong, it is agreeing with itself. `jsonschema` is not a
    #     dependency of this harness, so the case is SKIPPED BY NAME rather than silently.
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("  skip  jsonschema cross-check (library not installed — stated, not silently passed)")
        return False
    else:
        import yaml as _yaml
        schema = json.loads((ROOT / packmanifest.MANIFEST_SCHEMA).read_text())
        validator = Draft202012Validator(schema)
        found = 0
        for manifest in sorted((ROOT / "languages").rglob("tools.yaml")):
            doc = _yaml.safe_load(manifest.read_text())
            found += len(list(validator.iter_errors(doc)))
            assert not packmanifest.manifest_errors(
                manifest.parent.relative_to(ROOT / "languages").as_posix()), f"own validator rejects {manifest}"
        assert found == 0, f"jsonschema rejects {found} manifest constraint(s) this harness accepted"
        broken = _yaml.safe_load((ROOT / "languages/python/tools.yaml").read_text())
        broken["policy"]["warnings"] = "sometimes"
        assert list(validator.iter_errors(broken)), "the planted defect must fail the library too"
        CASES.append(("jsonschema agrees with this harness on every manifest",
                      "a validator that only ever agrees with itself"))
        print("  ok    jsonschema cross-check: 0 disagreements over every manifest")
        return True


def _version_and_closure_cases() -> None:
    """The 2.29.0 cases, split out of main() when it crossed the shape cap: a version read at its
    declared line, not anywhere in the file, and a dependency count that must be the closure."""
    # THE SHAPE THAT SLIPPED THROUGH AT 2.28.0: the declared line is stale while the current version
    # still appears ELSEWHERE in the same file. The old "anywhere in the file" rule passed this.
    _old = ".".join(("0", "0", "1"))
    with mutated("MODEL.md", lambda t, o=_old: t.replace(f"version: {_VERSION}**", f"version: {o}** (was {_VERSION})", 1)):
        case("a stale declared version line FAILS though the file still names VERSION elsewhere",
             "a skew check satisfied by any rendering of the version, such as a generated stamp", True,
             "MODEL.md states '0.0.1'")
    with mutated("atlas.yaml", lambda t: t.replace("version_sites:", "version_sites_retired:", 1)):
        case("an empty version-site roster FAILS", "a skew check over zero files, which passes forever", True,
             "version mismatch: version_sites")

    # A FALSE MINIMUM (2.28.0): a dependency count typed from direct lines, not the closure an install pulls.
    with mutated("atlas.yaml", lambda t: t.replace("    resolved_closure: 1", "    resolved_closure: 0", 1)):
        case("a dependency count below the locked closure FAILS", "\"1 dependency\" printed while the lock "
             "installs more", True, "the count an install pays is the closure")
    with mutated("ABOUT.md", lambda t: t.replace("\n", "\nInstalls in 184 KiB.\n", 1)):
        case("a size typed into an entry document FAILS", "a footprint figure true on the day it was typed",
             True, "a size typed into prose")
    with mutated("docs/VERIFY.md", lambda t: t.replace("# ", "# \u200b", 1)):
        case("an invisible character in a tracked file FAILS", "an instruction a reviewer cannot see, "
             "handed to every model that reads the tree", True, "carries invisible U+200B")
    with mutated("docs/VERIFY.md", lambda t: t.replace("# ", "# See `scripts/no_such_instrument.py`. ", 1)):
        case("a backticked path that does not exist FAILS", "a mechanism named in prose that nothing implements",
             True, "which does not exist")
    with mutated("atlas.yaml", lambda t: t.replace("  - [unit_tests, tests, focused_tests]\n", "", 1)):
        case("two gates resolving to one command, undeclared, FAIL", "race_detection passed by running the unit "
             "tests: many gate names, one check", True, "gate collision")
    # THE INTAKE LINE IS PLANTED, NOT BORROWED: the first fixture named `intake: 3.0.0`, the second read a
    # live one — both broke when their entry graduated (a_fixture_that_names_what_it_could_read). Every
    # unenforceable entry is a valid host, and one always exists.
    with mutated("atlas.yaml", lambda t: t.replace("    unenforceable:", "    intake: 0.1.0\n    unenforceable:", 1)):
        case("a failure left in intake past two minor versions FAILS", "a recorded mistake that never "
             "becomes a guard — a promise to come back, kept as an exemption", True, "has sat in intake since")
    # `gate <file>` WITH NO GATE: one numbered, runnable line per gate the change needs (3.3.0).
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        _rc = atlas.gate("examples/rust/bounded_retry.rs", None, False)
    _want = len(atlas.required_gates({"change_class": "source_change"}))
    _got = [line for line in _buf.getvalue().splitlines() if line[:1].isdigit()]
    if _rc != 0 or len(_got) != _want:
        raise SystemExit(f"FAIL gate <file> printed {len(_got)} numbered line(s), rc={_rc}; wanted {_want}, rc=0")
    CASES.append(("gate <file> with no gate lists every gate the change needs",
                  "a first-time user forced to learn the gate vocabulary before getting any answer"))
    print("  ok    gate <file> with no gate lists every gate the change needs")
    _quoted = re.search(r"^  root_cause_outside_scope: \{closed_by: '([^']*)'\}$", (ROOT / "atlas.yaml").read_text(), re.M)
    with mutated("atlas.yaml", lambda t, m=_quoted: t.replace(m.group(0), m.group(0).replace("'", ""), 1)):
        case("a YAML flow value split on a comma FAILS", "a declaration that loads half its text and passes",
             True, "a flow value split on a comma")
    # GENERATED VALUES ROUND-TRIP (3.3.0): every value safeedit.yaml_value emits must read back exactly as
    # a plain value AND inside a {flow} mapping — seeded strings over YAML's special characters.
    import random as _random

    import safeedit
    from atlascore import strict_yaml as _sy
    _rng = _random.Random(7)
    _alphabet = "ab ,:'\"#-{}[]&*!|>%@`?\\"
    _samples = ["the task owner, who widens it", "it's a, b: c", "yes", "- dash", "#x", "{b}"]
    _samples += ["".join(_rng.choice(_alphabet) for _ in range(_rng.randint(1, 12))) for _ in range(400)]
    for _text in _samples:
        _out = safeedit.yaml_value(_text)
        if (_sy(f"k: {_out}", "t").get("k") != _text
                or _sy(f"k: {{v: {_out}}}", "t").get("k") != {"v": _text}):
            raise SystemExit(f"FAIL yaml_value({_text!r}) -> {_out!r} does not read back")
    CASES.append((f"yaml_value round-trips {len(_samples)} hostile strings in plain and flow position",
                  "a hand-quoted YAML value that loads as something else, or as half of itself"))
    print(f"  ok    yaml_value round-trips {len(_samples)} hostile strings in plain and flow position")
    # ENFORCEMENT AT COMMIT (3.4.0): a good file passes, a broken copy is refused, and an installed hook
    # blocks the commit in a real repository. Python is the one toolchain every CI runner has.
    import subprocess as _sp
    import tempfile as _tf

    import enforce
    if enforce.check_file(ROOT / "examples/python/bounded_async.py")[0] != "PASS":
        raise SystemExit("FAIL enforce refuses a correct Python example")
    with _tf.TemporaryDirectory() as _repo:
        _bad = Path(_repo) / "bad.py"
        _bad.write_text("def broken(:\n", encoding="utf-8")
        if enforce.check_file(_bad)[0] != "FAIL":
            raise SystemExit("FAIL enforce passed a Python syntax error")
        _sp.run(["git", "init", "-q", _repo], check=True, timeout=600)
        _sp.run([sys.executable, str(ROOT / "scripts/enforce.py"), "install"], cwd=_repo, check=True, capture_output=True, timeout=600)
        _left = _sp.run(["git", "status", "--porcelain", "--ignored"], cwd=_repo, capture_output=True, text=True, check=True, timeout=600).stdout
        if _left.strip() != "?? bad.py":
            raise SystemExit(f"FAIL enforce install wrote outside the git hook: {_left!r}")
        _sp.run(["git", "add", "bad.py"], cwd=_repo, check=True, timeout=600)
        _commit = _sp.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
                          cwd=_repo, capture_output=True, text=True, timeout=600)
        if _commit.returncode == 0:
            raise SystemExit("FAIL the installed pre-commit hook let a syntax error commit")
    CASES.append(("enforce refuses a broken file, and its hook blocks the commit",
                  "rules an agent can read and skip — a long system prompt with no enforcement behind it"))
    print("  ok    enforce refuses a broken file, and its hook blocks the commit")
    # A LANDING REFUSES A RED CLEAN CHECKOUT (3.4.0): the gate runs in the landing, not in a habit.
    import branchstate
    if branchstate.clean_checkout_errors(((("-c", "raise SystemExit(0)")),)) is not None:
        raise SystemExit("FAIL clean_checkout_errors refused a passing gate")
    if branchstate.clean_checkout_errors(((("-c", "raise SystemExit(3)")),)) is None:
        raise SystemExit("FAIL clean_checkout_errors let a failing gate through")
    CASES.append(("a landing refuses when a clean checkout of HEAD fails its gates",
                  "a verdict printed and not gated — clean=1 on screen and the lane landed anyway"))
    print("  ok    a landing refuses when a clean checkout of HEAD fails its gates")
    _lang = (ROOT / "scripts/langbar.py").read_text()
    _bound = re.search(r",? ?timeout=600", _lang).group(0)
    with mutated("scripts/langbar.py", lambda t, b=_bound: t.replace(b, "", 1)):
        case("a subprocess call with no timeout FAILS", "a hung tool that ends a run and loses its results",
             True, "runs a subprocess with no timeout")
    import staleness
    _out = io.StringIO()
    with contextlib.redirect_stdout(_out):
        staleness.oldest(3)
        staleness.worktrees()
        staleness.review()
    # A SQUASH-MERGED LANE IS FINISHED (3.6.1): commits ahead, tree identical to the base.
    if not staleness.lane_verdict(False, False, 0.0, 0, 1, True).startswith("FINISHED") \
            or staleness.lane_verdict(False, False, 0.0, 0, 1, False) != "active" \
            or staleness.lane_verdict(True, False, 0.0, 0, 0, True) != "main checkout":
        raise SystemExit("FAIL staleness called a squash-merged lane active, or a lane with new work finished")
    if any(s not in _out.getvalue() for s in ("main checkout", "least recently edited", "drift review:")):
        raise SystemExit("FAIL staleness did not report the oldest files, or offered the main checkout for removal")
    CASES.append(("staleness names the oldest edits and never offers the main checkout for removal",
                  "a finished-lane report that tells an agent to delete the main checkout"))
    print("  ok    staleness names the oldest edits and never offers the main checkout for removal")
    # THE SOLO SCORER IS SENSITIVE (3.6.0): a fake agent that commits broken code must score committed_broken
    # without the hook and no_commit with it — or a "no difference" result means nothing.
    import workflowbench as _wb

    def _fake(prompt, model, cwd, tools, timeout):
        target = Path(cwd) / "calc.py"
        target.write_text(target.read_text() + "\ndef median(xs):\n    return (\n")
        _sp.run(["git", "commit", "-qam", "add"], cwd=cwd, capture_output=True, timeout=60)
        return ""
    _real, _wb._claude = _wb._claude, _fake
    try:
        _bare, _hook = _wb.solo_run("x", "bare", 60), _wb.solo_run("x", "hook", 60)
    finally:
        _wb._claude = _real
    if (_bare, _hook) != ("committed_broken", "no_commit"):
        raise SystemExit(f"FAIL solo scorer: a broken commit scored {_bare} bare and {_hook} with the hook")
    CASES.append(("the solo workflow scorer sees a broken commit, and the hook refuses it",
                  "a benchmark reporting 'no difference' because it could not see the difference"))
    print("  ok    the solo workflow scorer sees a broken commit, and the hook refuses it")
    import importlib.metadata as _md
    _real_requires = _md.requires
    _md.requires = lambda name: ["planted-subdependency>=1"] if name == "pyyaml" else _real_requires(name)
    try:
        case("a sub-dependency the lock does not pin FAILS", "an upstream release that quietly grows its own "
             "dependencies, read as still one", True, "the lock does not pin: planted-subdependency")
    finally:
        _md.requires = _real_requires


def main() -> int:
    # A READ-ONLY CALLER NEVER PLANTS (3.9.0): an audit agent ran this suite beside a live editor.
    if os.environ.get("THEA_READ_ONLY"):
        raise SystemExit("THEA_READ_ONLY is set: this suite PLANTS defects in tracked files — refused. Read-only "
                         "checks: atlas.py check, astshape.py, contextcost.py, ruff check .")
    _lock = suite_lock()  # noqa: F841 — held for the whole run, released at exit
    os.environ["THEA_SUITE_PID"] = str(os.getpid())  # this process may write while it holds the lock
    # A TIMEOUT SENDS SIGTERM: turn it into an exit, so every `finally` restore runs (3.13.0).
    import signal
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    for line in safeedit.restore_leftovers(ROOT):
        print(f"  restored a plant a killed run left behind: {line}")
    print("atlas contract — mutation tests")

    # 0. SPECIFICITY FIRST. A guard that fires on the real tree gets silenced,
    #    so the unmutated repository must pass before any defect is planted.
    case("a clean tree passes", "a check so strict it fires on correct content", False, "contract")

    # 1. GENERATED-BLOCK DRIFT — the reviewer's risk: a doc edited by hand.
    # THE ANCHOR IS DERIVED FROM A BLOCK THAT LIVES IN MODEL.md NOW. The gates table moved to the
    # README only at 2.28.0, and a fixture that typed `source_change` would have planted nothing here.
    _role = (atlas.atlas().get("runtime_roles") or {}).get("zed") or "multi_agent_host"
    _role = str(_role.get("role") if isinstance(_role, dict) else _role)
    with mutated("MODEL.md", lambda t: t.replace(f"`{_role}`", f"`{_role}_edited`", 1)):
        case("a hand-edited generated block FAILS", "a generator nobody checks the output of", True, "generated block")

    # 2. The generator must be the thing that repairs it, and be idempotent.
    with mutated("MODEL.md", lambda t: t.replace(f"`{_role}`", f"`{_role}_edited`", 1)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            atlasgen.index(write=True)
        case("index --write repairs the drift it detects", "a check that reports drift nothing can fix", False)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        atlasgen.index(write=True)
    assert "wrote" not in buf.getvalue(), "index --write is not idempotent: a second run rewrote a file"
    CASES.append(("index --write is idempotent", "a generator that rewrites on every run, so drift is invisible in diffs"))
    print("  ok    index --write is idempotent")

    # 3. VERSION SKEW across the six declared sites.
    with mutated("VERSION", lambda t: "0.0.1\n"):
        case("a version skew FAILS", "six files free to disagree about which contract this is", True, "version mismatch")
    _version_and_closure_cases()

    # 4. MANIFEST SCHEMA — the reviewer's 'policy says it, nothing proves it'.
    with mutated("languages/python/tools.yaml", lambda t: t.replace("policy:", "policies:", 1)):
        case("a manifest missing a top-level key FAILS", "an existence check passing a manifest with no policy", True, "manifest missing key")
    with mutated("languages/python/tools.yaml", lambda t: t.replace("language: python", "language: pyhton", 1)):
        case("a manifest whose identity disagrees FAILS", "a rust manifest copied into the python pack", True, "identity mismatch")
    with mutated("languages/python/tools.yaml", lambda t: t.replace("  blockers:", "  blokers:", 1)):
        case("a manifest missing a policy key FAILS", "a manifest that declares no blockers and still gates a change", True, "policy missing")

    # 4b. THE MANIFEST GRAMMAR (1.3.0) — prose in a field an instrument has to evaluate.
    with mutated("languages/python/tools.yaml", lambda s: s.replace("  test: pytest", "  test: Test (stdlib)", 1)):
        case("a prose entry in a tool field FAILS", "49% of declared entries sitting in binary fields, "
             "so no instrument could evaluate them and the packs read as complete", True, "does not match the declared form")
    with mutated("languages/python/tools.yaml", lambda s: s.replace("  warnings: non_blocking", "  warnings: sometimes", 1)):
        case("a value outside a declared enum FAILS", "a hand-written validator that reads `required` and "
             "silently ignores every other keyword", True, "is not one of")
    # The anchor is DERIVED from the schema, never typed: a literal `"const": 1` stopped matching
    # the moment the manifest format moved to 2, and the harness refused — correctly — rather than
    # planting nothing. A fixture that names a version has to be re-typed at every bump.
    _format = json.loads((ROOT / packmanifest.MANIFEST_SCHEMA).read_text())["properties"]["schema"]["const"]
    _anchor = f'"const": {_format},'
    with mutated("tools/tools.schema.json", lambda s, a=_anchor: s.replace(a, a + ' "multipleOf": 7,', 1)):
        case("a schema keyword the harness cannot check FAILS LOUDLY", "a validator that skips an unknown "
             "keyword and prints a clean pass over an unchecked constraint", True, "keyword not implemented")

    # 4c. THE INSTRUMENT ROSTER — a limit with no owner, and a script nobody announces.
    with mutated("atlas.yaml", lambda s: s.replace(
            "    closed_by: '`atlas.py check`, which it calls'", "    closed_by: ''", 1)):
        case("an instrument whose limit has no closer FAILS", "a table of blind spots that ages into a "
             "table of defects because no row names who closes it", True, "limit with no owner")
    with mutated("atlas.yaml", lambda s: s.replace("    script: scripts/ghaudit.py", "    script: scripts/gone.py", 1)):
        case("an instrument naming a missing file FAILS", "a roster that describes an instrument the tree "
             "does not have", True, "does not exist")

    # 4d. A GENERATED FILE, not only a generated block.
    with mutated("llms.txt", lambda s: s.replace("# Thea Software", "# Thea Softwar", 1)):
        case("a hand-edited generated file FAILS", "an agent-facing index maintained by hand, which narrows "
             "the moment something is added beside it", True, "generated file drifted")

    # 4e. DATES (1.3.1) — a claim stamped with a calendar date instead of a contract version.
    # The date is ASSEMBLED, never written: a literal here would be a dated claim in a tracked
    # file, so the guard would fire on its own test fixture and the clean sweep would fail.
    planted_date = "-".join(("2026", "01", "02"))
    with mutated("docs/VERIFY.md", lambda s: s.replace("# ", f"# Measured {planted_date} — ", 1)):
        case("a calendar date in a tracked file FAILS", "a measurement stamped with when somebody typed, "
             "which no later reader can re-check against anything", True, "calendar date in")
    # A STALE CURRENT-VERSION CLAIM (2.28.0): the README nav read v2.26.0 two releases on. The planted
    # version is DERIVED from VERSION, so the fixture can never collide with the real one.
    _stale = ".".join(str(int(x) + 1) for x in _VERSION.split("."))
    with mutated("docs/VERIFY.md", lambda s, v=_stale: s.replace("# ", f"# Thea, contract v{v} — ", 1)):
        case("a typed contract version that is not VERSION FAILS", "a navigation line naming a release the "
             "tree left behind, beside a badge that serves the right one", True, "as current; VERSION is")
    # THE ANCHOR IS READ FROM THE FILE, NOT TYPED. This fixture spelled the version as
    # `since: '0.9.5'`; a later re-dump wrote it unquoted, the pattern stopped matching, and the
    # harness refused rather than planting nothing — which is the behaviour, but it is the second
    # fixture this session to name a value it could have read.
    _since = re.search(r"^  since:.*$", (ROOT / "languages/python/tools.yaml").read_text(), re.M).group(0)
    with mutated("languages/python/tools.yaml", lambda s, a=_since: s.replace(a, "  since: 'recently'", 1)):
        case("a provenance version that is not a version FAILS", "provenance that reads as measured when it "
             "was recalled", True, "does not match the declared form")

    # 4f. HTML LINKS (2.1.0) — the README header is HTML, and none of it was checked.
    with mutated("README.md", lambda s: s.replace('src="docs/assets/', 'src="docs/assets/gone-', 1)):
        case("a broken HTML src FAILS", "a Markdown link checker reporting a clean pass over every anchor "
             "and image in the page a reader sees first", True, "broken local link")

    # 5. LABEL ROUTING — a route printing a label nobody created.
    with mutated("config/github-labels.json", lambda t: t.replace('"lang/python"', '"lang/pythonx"', 1)):
        case("a route whose label is not in the catalog FAILS", "atlas printing lang/quantum/qsharp, a label that never existed", True, "route label not in")

    # 6. A ROUTE WITH NO PACK.
    with mutated("atlas.yaml", lambda t: t.replace("  '.py': python", "  '.py': pythonx", 1)):
        case("a route pointing at a missing pack FAILS", "an artifact_routes entry with nothing behind it", True)

    # 6b. A DUPLICATE EXTENSION (2.3.0) — YAML keeps the last key and says nothing.
    with mutated("atlas.yaml", lambda s: s.replace("  '.py': python\n", "  '.py': python\n  '.py': rust\n", 1)):
        case("an extension declared twice FAILS", "a route silently taken over by a later line, which is "
             "how every F# file moved to the Forth pack with no error", True, "more than once")

    # 6c. A CORRUPTED SOURCE FILE (2.4.0) — the contract read documents and never asked whether its
    #     own harness was still valid Python. A mechanical re-indent wrote a file that did not
    #     compile, twice, and every count still printed.
    with mutated("scripts/doctor.py", lambda s: s.replace("def findings()", "def findings(", 1)):
        case("a source file that does not parse FAILS", "a contract that validates every document and "
             "never asks whether its own code still compiles", True, "not valid Python")

    route_ambiguity_cases()
    property_sweep()

    # 8. HARD INVARIANTS — every name owned, and each check kills a real defect.
    violations, enforced, declared = atlasinv.invariants()
    assert not violations, f"invariants unowned or violated on a clean tree: {violations}"
    assert len(enforced) + len(declared) == len(atlas.atlas().get("hard_invariants")), "an invariant is neither enforced nor declared"
    with mutated("atlas.yaml", lambda t: t.replace("  - ci_enforces_contract\n", "  - ci_enforces_contract\n  - invented_invariant\n", 1)):
        case("an invariant with no owner FAILS", "a list of promises that accrues authority from being written down", True, "neither checked nor declared")
    with mutated(".github/workflows/atlas-ci.yml", lambda t: t.replace("python scripts/atlas.py check", "true", 1)):
        case("CI not running the contract FAILS ci_enforces_contract", "the invariant that says CI enforces, asserted by nothing", True, "ci_enforces_contract")
    with mutated("languages/python/tools.yaml", lambda t: t.replace("compiler_or_runtime: python3", "compiler_or_runtime:", 1)):
        case("a manifest naming no runtime FAILS native_language_tools_are_authoritative", "'native tools are authoritative' with no native tool named", True, "native_language_tools")

    promoted_invariant_cases()

    # SPECIFICITY, asserted once for the whole set: the clean tree satisfies all 25.
    violations, enforced, declared = atlasinv.invariants()
    _all = len(atlas.atlas().get("hard_invariants") or [])
    assert not violations and len(enforced) == _all and not declared, \
        f"clean tree: {len(enforced)} enforced, {len(declared)} declared, violations={violations}"
    CASES.append((f"all {_all} invariants pass on a clean tree", "checks so loose or so strict they cannot be trusted"))
    print(f"  ok    all {_all} invariants enforced and satisfied on a clean tree")


    agent_and_entry_cases()

    external_api_cases()
    knowledge_and_action_cases()
    import cli_test  # install, CLI and MCP cases, counted in THIS module's CASES
    cli_test.run(sys.modules[__name__])
    retrieval_cases()

    # 9. THE ENTRY POINT the reviewer called brittle: it must work from anywhere.
    out = shutil.which("python3")
    assert out, "python3 not on PATH"
    for cwd in (ROOT, ROOT / "scripts", Path("/tmp")):
        r = subprocess.run([out, str(ROOT / "scripts" / "check_contract.py")], cwd=cwd, capture_output=True, text=True, check=False, timeout=600)
        assert r.returncode == 0, f"check_contract.py failed from {cwd}: {r.stderr[-300:]}"
    CASES.append(("check_contract.py runs from any working directory", "an entry point that only works from scripts/"))
    print("  ok    check_contract.py runs from repo root, scripts/ and /tmp")

    # 9a. THE ENVIRONMENT DOCTOR — it must answer for every declared instrument, not a copy of
    #     the roster. A second list would narrow the moment an instrument is added beside it.
    import doctor as _doctor
    rows = _doctor.findings()
    declared = atlas.atlas().get("instruments") or {}
    instrument_row = next(r for r in rows if r["capability"] == "instrument files")
    assert instrument_row["measured"].endswith(f"/{len(declared)} present"), \
        f"doctor counts {instrument_row['measured']} against {len(declared)} declared instruments"
    assert [r for r in rows if r["required"]], "doctor marks nothing as required"
    assert all(r["costs_if_absent"] for r in rows), "a doctor row must say what its absence costs"
    CASES.append(("doctor answers for every declared instrument",
                  "a second roster of instruments that narrows silently beside the first"))
    print("  ok    doctor: every declared instrument answered for, every row states its cost")

    cross_checked = jsonschema_cross_check()
    # THE RUNNING MODULE IS PASSED IN, never re-imported: as __main__ it is not `atlas_test`, and a
    # sibling that imported `atlas_test` would get a SECOND copy whose CASES nobody counts.
    import atlas_guards_test
    atlas_guards_test.run(sys.modules[__name__])

    # The count is MEASURED, not intended: the first draft said 14 against 12 real cases, and an
    # expectation nobody counted fails every run for the wrong reason. The cross-check case is
    # counted only when it RAN, so an absent library cannot quietly reduce the total.
    expected = 153 + (1 if cross_checked else 0)
    if len(CASES) != expected:
        raise SystemExit(f"CASE COUNT MOVED: {len(CASES)} ran, {expected} expected — a harness that silently skips cases prints a full pass")
    print(f"atlas tests: {len(CASES)}/{expected} pass")
    print("SCOPE: these test the CONTRACT. Whether a declared tool EXISTS and RUNS is")
    print("       `python scripts/packprobe.py --mode smoke`; whether the live GitHub controls")
    print("       match the declaration is `python scripts/ghaudit.py`. Neither is left to prose.")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--restore"]:
        _lines = safeedit.restore_leftovers(ROOT)
        print("\n".join(_lines) or "no plant was left behind")
        raise SystemExit(1 if any("left alone" in x for x in _lines) else 0)
    raise SystemExit(main())
