#!/usr/bin/env python3
"""The guards added at 2.27.0-2.28.0, split out of atlas_test.py to keep it under the shape cap. Named *_test.py because it IS a
test harness, and the loader-bypass guard exempts test harnesses by that convention.

Each case plants a defect and asserts the contract refuses it, exactly as the cases in
atlas_test.py do, and registers into ITS counted CASES — which is why run() takes the running
module rather than importing atlas_test: run as a script that module is __main__, and a fresh
`import atlas_test` would be a second copy whose cases nobody counts.
"""
from __future__ import annotations

import contextlib
import io
import subprocess

T = None  # the running atlas_test module, bound by run()


def run(module) -> None:
    global T, ROOT, CASES, case, mutated, atlas, suite_lock
    T = module
    ROOT, CASES, case, mutated, atlas, suite_lock = (module.ROOT, module.CASES, module.case,
                                                     module.mutated, module.atlas, module.suite_lock)
    parse_budget_cases()
    editorconfig_cases()
    landing_cases()
    readme_figure_cases()
    precommit_cases()
    decision_cases()
    spec_conformance_cases()
    anti_silent_cases()
    prepush_cases()
    process_condition_cases()
    bare_sleep_cases()
    accident_ledger_cases()


def parse_budget_cases() -> None:
    """The parse budget and the strict-loader bypass, each with the defect planted."""
    # 9c. PARSE BUDGET — THE REGRESSION THIS SESSION INTRODUCED, MADE UNREPEATABLE. At 2.26.0 one
    #     check() parsed ~37 files 671 times; 315 of those came from a new coverage rule that looked
    #     up a manifest per (pack, role) pair. The bound is DERIVED, not typed: a check parses each
    #     tracked YAML file at most once, so there is no number here to go stale.
    import atlascore as _core
    import yaml as _y
    _yaml_files = len([p for p in _core.tracked() if p.suffix in (".yaml", ".yml")])

    def _cold_parses() -> int:
        seen = [0]
        real = _y.load

        def counting(*a, **k):
            seen[0] += 1
            return real(*a, **k)
        _y.load = counting
        try:
            _core._PARSED.clear()
            _core._PARSED_BYTES[0] = 0
            atlas.atlas.cache_clear()
            with contextlib.redirect_stdout(io.StringIO()):
                atlas.check()
        finally:
            _y.load = real
        return seen[0]
    parses = _cold_parses()
    assert parses <= _yaml_files, (f"one check() parsed YAML {parses} times over {_yaml_files} "
                                   "tracked files — something re-parses per lookup")
    # MUTATION: disable the cache, and the budget must fail. A guard that cannot fail is decoration.
    # A builtin dict's methods are read-only, so the mutation swaps the whole store for one that
    # never remembers. strict_yaml reads the module global at call time, so the swap is seen.
    class _Forgetful(dict):
        def get(self, key, default=None):
            return default
    _kept = _core._PARSED
    _core._PARSED = _Forgetful()
    try:
        uncached = _cold_parses()
    finally:
        _core._PARSED = _kept
    assert uncached > _yaml_files, (f"with the cache disabled the budget still passed ({uncached} <= "
                                    f"{_yaml_files}) — the guard cannot see the regression it exists for")
    CASES.append((f"one check() parses each of {_yaml_files} YAML files at most once ({parses}; "
                  f"{uncached} with the cache planted off)",
                  "a lookup that re-parses per call, which cost 73% of a check at 2.26.0"))
    print(f"  ok    parse budget: {parses} parses over {_yaml_files} files; {uncached} uncached, refused")

    # 9d. NO BYPASS OF THE STRICT LOADER. Plant a direct yaml.safe_load in a real module; the
    #     contract must refuse it, naming the file.
    with mutated("scripts/doctor.py",
                 lambda s: s + "\n\ndef _planted():\n    import yaml\n    return yaml.safe_load('a: 1')\n"):
        case("a module calling yaml.safe_load directly is refused",
             "a YAML read that skips the duplicate-key refusal and the parse cache",
             expect_fail=True, needle="calls yaml.safe_load directly")


def editorconfig_cases() -> None:
    """The [*] section is enforced: plant a file without its final newline and the contract fails."""
    with mutated("docs/INDEX.md", lambda s: s.rstrip("\n")):
        case("a tracked file missing its final newline is refused",
             "an .editorconfig that exists and that nothing obeys",
             expect_fail=True, needle="has no final newline")


def landing_cases() -> None:
    """Push and merge are one step: a pushed lane nothing will merge is refused, not reported done."""
    from branchstate import landing_verdict
    armed = {"number": 7, "state": "OPEN", "autoMergeRequest": {"mergeMethod": "REBASE"}}
    open_unarmed = {"number": 7, "state": "OPEN", "autoMergeRequest": None}
    table = [
        ((True, False, open_unarmed, True), "STRANDED"),   # the shape found twice in this repository
        ((True, False, None, True), "STRANDED"),           # pushed with no pull request at all
        ((True, False, {"number": 7, "state": "CLOSED"}, True), "STRANDED"),
        ((True, False, armed, False), "unknown"),          # the forge did not answer: refuse to guess
        ((True, False, armed, True), "armed"),
        ((True, True, None, True), "merged"),
        ((False, False, None, True), "local"),
    ]
    for args, want in table:
        got = landing_verdict(*args)
        assert got.startswith(want), f"landing_verdict{args} said {got!r}, expected {want}"
    import branchstate as _bs
    calls = []

    def flaky_once(branch):
        calls.append(branch)
        return 1 if len(calls) == 1 else 0
    real, _bs._land_once = _bs._land_once, flaky_once
    try:
        assert _bs.land("lane") == 0 and len(calls) == 2, f"a race was not retried: {len(calls)} attempt(s)"
        calls.clear()
        _bs._land_once = lambda branch: calls.append(branch) or 1
        assert _bs.land("lane") == 1 and len(calls) == 2, f"a second failure retried again: {len(calls)}"
    finally:
        _bs._land_once = real
    from branchstate import untagged_version
    assert untagged_version("2.27.0", {"v2.8.0", "v2.7.3"}) == "v2.27.0", "an untagged VERSION went unnoticed"
    assert untagged_version("2.27.0", {"v2.27.0"}) is None, "a tagged VERSION was re-tagged"
    assert untagged_version("", set()) is None, "an empty VERSION invented a tag"
    CASES.append((f"landing: {len(table)} states, a pushed lane with nothing armed is STRANDED",
                  "work reported pushed while nothing would ever merge it"))
    print(f"  ok    landing: {len(table)} states classified, the stranded lane refused")


def anti_silent_cases() -> None:
    """The three silent failures found at 2.27.0, each planted: an erased concurrent write, an
    anchored edit that did nothing, and a second suite interleaving with this one."""
    from safeedit import replace_once as _once
    target = ROOT / "docs" / "INDEX.md"
    original = target.read_bytes()
    try:
        with mutated("docs/INDEX.md", lambda s: s + "\nPLANTED\n"):
            target.write_text(target.read_text() + "\nCONCURRENT\n")
    except SystemExit as exc:
        assert "CONCURRENT WRITE" in str(exc), f"refused for the wrong reason: {exc}"
    else:
        raise SystemExit("FAIL a concurrent write during a planted defect was ERASED silently")
    kept = sorted(target.parent.glob("INDEX.md.concurrent-*"))
    assert kept and b"CONCURRENT" in kept[-1].read_bytes(), "the other writer's version was lost"
    assert target.read_bytes() == original, "the planted defect was left in the tree"
    for sidecar in kept:
        sidecar.unlink()
    for text, anchor in (("abc", "zzz"), ("abab", "ab")):
        try:
            _once(text, anchor, "X", "planted")
        except ValueError:
            continue
        raise SystemExit(f"FAIL replace_once accepted {text.count(anchor)} matches of {anchor!r}")
    try:
        second = suite_lock()
    except SystemExit as exc:
        assert "REFUSING to interleave" in str(exc)
    else:
        second.close()
        raise SystemExit("FAIL a second suite acquired the lock this one holds")
    CASES.append(("a concurrent write is kept, a 0- or 2-match anchor refused, a second suite refused",
                  "a restore that erases an edit, an insert that does nothing, two suites interleaving"))
    print("  ok    anti-silent: concurrent write kept, anchor refused at 0 and 2 matches, lock held")


def prepush_cases() -> None:
    """A lane is never pushed bare: the hook refuses it, and admits only what cannot strand."""
    import os as _os
    hook = ROOT / ".githooks" / "pre-push"
    sha, zero = "a" * 40, "0" * 40
    table = [
        (f"refs/heads/feat/x {sha} refs/heads/feat/x {zero}", {}, 1),               # the bare push
        (f"refs/heads/feat/x {sha} refs/heads/feat/x {zero}", {"ATLAS_LANDING": "1"}, 0),
        (f"(delete) {zero} refs/heads/feat/x {sha}", {}, 0),                          # a delete
        (f"refs/heads/main {sha} refs/heads/main {zero}", {}, 0),                     # the ruleset's job
        (f"refs/tags/v1 {sha} refs/tags/v1 {zero}", {}, 0),                           # not a branch
    ]
    for line, extra, want in table:
        env = {k: v for k, v in _os.environ.items() if k != "ATLAS_LANDING"} | extra
        got = subprocess.run(["sh", str(hook), "origin", "url"], input=line + "\n", env=env,
                             capture_output=True, text=True, check=False).returncode
        assert got == want, f"pre-push on {line.split()[2]!r} with {extra or 'no env'}: exit {got}, wanted {want}"
    CASES.append((f"pre-push: a bare lane push refused, {len(table) - 1} legitimate pushes admitted",
                  "a lane pushed with nothing to merge it — stranded, looking finished"))
    print("  ok    pre-push: bare lane refused; --land, delete, main and tags admitted")


def process_condition_cases() -> None:
    """Every stop/escalate condition names who decides it; a silent one is refused."""
    import yaml as _y
    with mutated("atlas.yaml", lambda s: s.replace("  plan_drift: {decided_by: agentrun.plan_drift}\n", "", 1)):
        case("a process condition with no declared decider is refused",
             "a stop condition nothing decides — a stop that never fires",
             expect_fail=True, needle="no decider or closer is declared")
    with mutated("atlas.yaml", lambda s: s.replace("decided_by: agentrun.plan_drift", "decided_by: agentrun.no_such_fn", 1)):
        case("a decider naming a function that does not exist is refused",
             "an enforcer that is a name and not a function",
             expect_fail=True, needle="agentrun.no_such_fn")
    declared = _y.safe_load((ROOT / "atlas.yaml").read_text())["process_conditions"]
    coded = sum(1 for v in declared.values() if v.get("decided_by"))
    print(f"        conditions: {coded} decided by code, {len(declared) - coded} by a named closer")


def bare_sleep_cases() -> None:
    """Waiting is on a condition, through resilience.wait_until — never a bare fixed sleep."""
    with mutated("scripts/doctor.py", lambda s: s + "\n\ndef _planted():\n    import time\n    time.sleep(5)\n"):
        case("a bare time.sleep outside resilience is refused",
             "a fixed sleep standing in for a condition — too short on a slow day, wasted on a fast one",
             expect_fail=True, needle="calls time.sleep")


def accident_ledger_cases() -> None:
    """Every recorded accident resolves to the guard that refuses it, and a duplicate def is refused."""
    with mutated("atlas.yaml", lambda s: s.replace("enforced_by: [branchstate._pull_request,",
                                                   "enforced_by: [branchstate._no_such_guard,", 1)):
        case("an accident whose enforcer is not in the tree is refused",
             "a lesson whose guard was renamed or deleted, still read as protection",
             expect_fail=True, needle="branchstate._no_such_guard")
    with mutated("scripts/doctor.py", lambda s: s + "\n\ndef main():\n    return 0\n"):
        case("a module defining the same function twice is refused",
             "a later definition silently replacing the earlier one while every test passes",
             expect_fail=True, needle="defines main again")


def readme_figure_cases() -> None:
    """Every guarded README figure is planted stale in turn and must be refused — one structure,
    a table of figures. Two copies of this function were refused by astshape at 2.28.0."""
    table = [
        ("**140 of 140**", "**139 of 139**", "a stale defect total in the README is refused",
         "a count typed into prose that the next added case makes wrong", "defect tests and the suites declare"),
        ("loads **1,855 tokens**", "loads **1,838 tokens**", "a stale session-entry figure in the README is refused",
         "the entry cost typed twice and edited once — the fifth stale-count sighting", "contextcost measures"),
    ]
    for current, planted, name, kills, needle in table:
        with mutated("README.md", lambda s, c=current, p=planted: s.replace(c, p, 1)):
            case(name, kills, expect_fail=True, needle=needle)


def precommit_cases() -> None:
    """A red fast rung refuses the commit: plant a duplicate definition, run the hook, expect 1."""
    hook = ROOT / ".githooks" / "pre-commit"
    with mutated("scripts/doctor.py", lambda s: s + "\n\ndef main():\n    return 0\n"):
        red = subprocess.run(["sh", str(hook)], cwd=ROOT, capture_output=True, text=True, check=False)
    clean = subprocess.run(["sh", str(hook)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert red.returncode == 1 and "REFUSED" in red.stderr, f"a red rung did not refuse the commit: {red.returncode}"
    assert clean.returncode == 0, f"the hook refused a clean tree: {clean.stderr[:200]}"
    CASES.append(("pre-commit: a red fast rung refuses the commit; a clean tree passes",
                  "a commit landed on a red rung because a script printed the verdict and did not gate on it"))
    print("  ok    pre-commit: red rung refused, clean tree admitted")


def decision_cases() -> None:
    """A decision record is internally consistent and its proof exists: plant each defect in turn."""
    table = [
        ("    cache_aside: the application already owns the miss path", "    cache_sideways: the application already owns the miss path",
         "a decision choosing an option it does not offer is refused", "cache_sideways"),
        ("  proven_by: examples/python/caching_strategies.py", "  proven_by: examples/python/no_such_proof.py",
         "a decision proven by a file that is not in the tree is refused", "no_such_proof.py"),
    ]
    for current, planted, name, needle in table:
        with mutated("systems/decisions.yaml", lambda s, c=current, p=planted: s.replace(c, p, 1)):
            case(name, "a design record whose claims no instrument can check", expect_fail=True, needle=needle)


def spec_conformance_cases() -> None:
    """Every hand-rolled implementation of a spec agrees with a reference over EVERY instance here."""
    import subprocess as _sp

    import atlascore
    import packmanifest
    import yaml as _yaml
    # 1. JSON Schema `pattern` is an unanchored SEARCH (2020-12 §6.3.3), not a whole-string match.
    unanchored = {"type": "string", "pattern": "^https://"}
    assert not packmanifest.validate("https://example.org/x", unanchored, "p"), \
        "the validator anchors `pattern` at both ends — JSON Schema patterns are searches"
    assert packmanifest.validate("http://example.org", unanchored, "p"), "an unanchored pattern accepted a miss"

    # 2. The fast C YAML loader decides exactly what the reference Python loader decides, on every file.
    class _Reference(_yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            seen = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in seen:
                    raise ValueError("duplicate")
                seen.add(key)
            return super().construct_mapping(node, deep)
    files = [f for f in _sp.check_output(["git", "ls-files"], cwd=ROOT).decode().split() if f.endswith((".yaml", ".yml"))]
    differ = [f for f in files if _yaml.load((ROOT / f).read_text(), Loader=_Reference)
              != _yaml.load((ROOT / f).read_text(), Loader=atlascore.StrictLoader)]
    assert files and not differ, f"the fast loader and the reference disagree on {differ[:3]}"
    CASES.append((f"spec conformance: unanchored patterns, and the C loader equal to the reference on {len(files)} YAML files",
                  "a hand-written implementation that silently diverges from the spec it claims"))
    print(f"  ok    spec conformance: pattern is a search; C loader == reference on {len(files)} YAML files")
