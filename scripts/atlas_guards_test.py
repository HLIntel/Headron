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
import os
import subprocess
import sys
import tempfile
from pathlib import Path

T = None  # the running atlas_test module, bound by run()


def run(module) -> None:
    global T, ROOT, CASES, case, mutated, atlas, suite_lock
    T = module
    ROOT, CASES, case, mutated, atlas, suite_lock = (module.ROOT, module.CASES, module.case,
                                                     module.mutated, module.atlas, module.suite_lock)
    parse_budget_cases()
    editorconfig_cases()
    landing_cases()
    precommit_cases()
    decision_cases()
    spec_conformance_cases()
    cloudflare_cases()
    redundancy_cases()
    anti_silent_cases()
    prepush_cases()
    process_condition_cases()
    bare_sleep_cases()
    accident_ledger_cases()
    chat_cases()
    native_agent_tool_cases()
    gate_operand_cases()
    read_only_cases()
    verify_cases()
    hook_chain_cases()
    declaration_cases()
    sandbox_cases()


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
        second = suite_lock(wait=0)
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
                             capture_output=True, text=True, check=False, timeout=600).returncode
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


def precommit_cases() -> None:
    """A red fast rung refuses the commit: plant a duplicate definition, run the hook, expect 1."""
    hook = ROOT / ".githooks" / "pre-commit"
    with mutated("scripts/doctor.py", lambda s: s + "\n\ndef main():\n    return 0\n"):
        red = subprocess.run(["sh", str(hook)], cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
    clean = subprocess.run(["sh", str(hook)], cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
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
    files = [f for f in _sp.check_output(["git", "ls-files"], cwd=ROOT, timeout=600).decode().split() if f.endswith((".yaml", ".yml"))]
    differ = [f for f in files if _yaml.load((ROOT / f).read_text(), Loader=_Reference)
              != _yaml.load((ROOT / f).read_text(), Loader=atlascore.StrictLoader)]
    assert files and not differ, f"the fast loader and the reference disagree on {differ[:3]}"
    CASES.append((f"spec conformance: unanchored patterns, and the C loader equal to the reference on {len(files)} YAML files",
                  "a hand-written implementation that silently diverges from the spec it claims"))
    print(f"  ok    spec conformance: pattern is a search; C loader == reference on {len(files)} YAML files")


def cloudflare_cases() -> None:
    """A Worker's config routes by FILENAME (the declared project_manifest rule), and its gate
    resolves to the verified dry-run build — never to a deploy."""
    from agentpolicy import gate_command
    from atlascore import route_with_evidence
    for name in ("wrangler.toml", "wrangler.json", "wrangler.jsonc"):
        route, rule, _ = route_with_evidence(f"examples/cloudflare/{name}")
        assert (route, rule) == ("cloudflare", "project_manifest"), f"{name} routed to {route} by {rule}"
    route, rule, _ = route_with_evidence("tsconfig.json")
    assert route is None, f"an unrelated .json was captured by the filename rule: {route} by {rule}"
    argv, _ = gate_command("cloudflare", "compiler_or_typechecker")
    assert argv[:3] == ["wrangler", "deploy", "--dry-run"] and "--config" in argv, f"the build gate is {argv}"
    assert "deploy" not in " ".join(gate_command("cloudflare", "unit_tests")[0] or []), "a test gate deploys"
    CASES.append(("cloudflare: wrangler.{toml,json,jsonc} route by filename; the build gate is a dry run",
                  "a platform config that routes nowhere, or a gate that deploys instead of verifying"))
    print("  ok    cloudflare: filename routing, dry-run build gate, no deploy behind any gate")


def redundancy_cases() -> None:
    """A sentence repeated on one entry path is refused: copy one README sentence into MODEL.md."""
    readme = (ROOT / "README.md").read_text()
    start = readme.index("**The expensive break is the one whose output looks like success:**")
    line = readme[start:readme.index("\n\n", start)]
    with mutated("MODEL.md", lambda s: s + "\n" + line + "\n"):
        case("a paragraph repeated across one entry path is refused",
             "the same text paid for twice by every reader of that path", expect_fail=True, needle="paid for twice")


def chat_cases() -> None:
    """A chat process with no stop, and install text over its cap, are each refused."""
    with mutated("atlas.yaml", lambda s: s.replace("      stop_when: the roles agree — say so, do not invent conflict\n", "", 1)):
        case("a chat process with no stop condition is refused", "a chat loop told how to start and never how to end",
             expect_fail=True, needle="chat process perspectives has no stop_when")
    with mutated("atlas.yaml", lambda s: s.replace("  install_max_bytes: 1200", "  install_max_bytes: 100", 1)):
        case("chat install text over its byte cap is refused", "a paste-once block that grows in every session",
             expect_fail=True, needle="chat install text is")


def read_only_cases() -> None:
    """An editor refuses while another process's suite holds the worktree (3.9.0), and a read-only caller
    cannot start the suite. Kills: an audit that plants defects beside a live editor, silently."""
    import safeedit
    _mine = os.environ["THEA_SUITE_PID"]
    os.environ["THEA_SUITE_PID"] = "0"  # as seen from any OTHER process while this suite holds the lock
    try:
        safeedit.write_verified(Path(tempfile.gettempdir()) / "thea-readonly-probe.txt", "x")
        raise SystemExit("FAIL an edit landed while a mutating suite held the worktree")
    except OSError as refused:
        if "holds this worktree" not in str(refused):
            raise
    finally:
        os.environ["THEA_SUITE_PID"] = _mine
    ro = subprocess.run([sys.executable, str(ROOT / "scripts/atlas_test.py")], env={**os.environ, "THEA_READ_ONLY": "1"},
                        capture_output=True, text=True, timeout=600, check=False)
    if ro.returncode == 0 or "THEA_READ_ONLY" not in ro.stdout + ro.stderr:
        raise SystemExit("FAIL the mutating suite started under THEA_READ_ONLY")
    CASES.append(("an edit refuses while another suite holds the worktree, and THEA_READ_ONLY refuses the suite",
                  "a read-only audit planting defects beside a live editor, erased by its restore"))
    print("  ok    an edit refuses while another suite holds the worktree, and THEA_READ_ONLY refuses the suite")


def gate_operand_cases() -> None:
    """A PRINTED GATE CHECKS THE FILE, AND CHECKS ONLY (3.9.0): bare, the python check parsed zero files and
    exited 0, and the formatter gate rewrote the tree. Each case kills one of those implementations."""
    import atlas as _atlas
    rec = _atlas.gate_record("examples/python/bounded_async.py", "compiler_or_typechecker")
    if rec["argv"][-1] != "examples/python/bounded_async.py":
        raise SystemExit(f"FAIL a per-file gate printed no operand: {rec['argv']}")
    fmt = _atlas.gate_record("examples/python/bounded_async.py", "formatter")["argv"]
    if "--check" not in fmt:
        raise SystemExit(f"FAIL the formatter gate is not check-only: {fmt}")
    CASES.append(("a per-file gate prints its operand, and the formatter gate is check-only",
                  "a pasteable command that passes on zero files, or rewrites the repository"))
    print("  ok    a per-file gate prints its operand, and the formatter gate is check-only")
    with mutated("atlas.yaml", lambda t: t.replace("safeedit.replace_once refusing 0 or", "atlascore.replace_once refusing 0 or", 1)):
        case("a parser rule naming an enforcer nothing defines FAILS", "a roster row that names a function and passes on the name",
             True, "names an enforcer nothing defines")


def native_agent_tool_cases() -> None:
    """A RUNTIME KEEPS ITS OWN TOOLS (3.8.0): Thea adds to an agent's layer and never subtracts from it."""
    with mutated("atlas.yaml", lambda t: t.replace("    cursor: {tool_config: [.cursor/mcp.json", "    cursorx: {tool_config: [.cursor/mcp.json", 1)):
        case("a runtime with no native-tools declaration FAILS native_agent_tools_are_kept",
             "a runtime added to the roster whose tools nobody said it keeps", True, "declares nothing for runtime cursor")
    with mutated("atlas.yaml", lambda t: t.replace("  install_writes: [git_hooks/pre-commit, git_hooks/pre-commit.legacy]", "  install_writes: [git_hooks/pre-commit, .claude/settings.json]", 1)):
        case("an install writing a runtime's tool configuration FAILS native_agent_tools_are_kept",
             "an install that quietly rewrites the agent's own permissions", True, "inside a runtime's tool configuration")
    with mutated("models/claude/README.md", lambda t: t.replace("## Native tools stay\n", "## Tools\n", 1)):
        case("an adapter that never says its runtime keeps its tools FAILS native_agent_tools_are_kept",
             "the principle declared in the contract and absent where the runtime reads", True, "no 'Native tools stay' section")
    from nativetools import _disabling, parse_config
    if _disabling({"permissions": {"deny": ["Bash(*)"]}}, {"deny"}) != ["permissions.deny"] \
            or _disabling({"tools": {"write": False, "read": True}}, set()) != ["tools.write"] \
            or _disabling({"permission": {"bash": "deny", "edit": "allow"}}, set(), values={"deny"}) != ["permission.bash"] \
            or _disabling(parse_config("x.jsonc", '{// a comment\n "tools": {"read": true}}'), set()) \
            or _disabling({"permissions": {"allow": ["Bash(git:*)"], "deny": []}}, {"deny"}):
        raise SystemExit("FAIL nativetools._disabling misreads a tool configuration")
    CASES.append(("a tool configuration that denies or switches off a native tool is found, an empty deny is not",
                  "a checked-in settings file that disables the agent's shell, passing as configuration"))
    print("  ok    a tool configuration that denies or switches off a native tool is found, an empty deny is not")


def verify_cases() -> None:
    """A gate's verdict is its exit code, and a gate not run is never a pass (3.9.0)."""
    import verify
    failed = verify.run_gate({"id": "x", "argv": ["python", "-c", "raise SystemExit(3)"]})
    passed = verify.run_gate({"id": "y", "argv": ["python", "-c", "print('FAIL looks bad but exits 0')"]})
    crashed = verify.run_gate({"id": "c", "argv": ["python", "-c", "print('- WRONG ROUTE: expected'); raise ValueError('the cause')"]})
    said = verify.run_gate({"id": "s", "argv": ["python", "-c", "print('- WRONG ROUTE: expected'); print('FAIL the real one'); raise SystemExit(1)"]})
    if "the real one" not in said["why"]:
        raise SystemExit(f"FAIL verify blamed {said['why']!r}, not the suite's own FAIL line")
    if "the cause" not in crashed["why"]:
        raise SystemExit(f"FAIL verify blamed {crashed['why']!r}, not the traceback's cause")
    os.environ["THEA_READ_ONLY"] = "1"
    try:
        skipped = verify.run_gate({"id": "z", "argv": ["python", "-c", "pass"], "mutates": True})
    finally:
        del os.environ["THEA_READ_ONLY"]
    if (failed["verdict"], passed["verdict"], skipped["verdict"]) != ("FAIL", "PASS", "NOT RUN") \
            or verify.verdict_code([passed, skipped]) != 2 or verify.verdict_code([passed, failed]) != 1 \
            or verify.verdict_code([]) != 2 or verify.verdict_code([passed]) != 0:
        raise SystemExit(f"FAIL verify misreads a verdict: {failed['verdict']}, {passed['verdict']}, {skipped['verdict']}")
    with mutated("atlas.yaml", lambda t: t.replace("  - {id: lint, argv: [ruff, check, .], mutates: false}\n",
                 "  - {id: lint, argv: [ruff, check, .], mutates: false}\n  - {id: orphan, argv: [python, scripts/nothing_runs_me.py], mutates: false}\n", 1)):
        case("a done-set gate no workflow runs FAILS ci_enforces_contract",
             "a gate verify runs locally and nothing runs on a pull request", True, "nothing runs it on a pull request")
    CASES.append(("verify reads the exit code, not the text, and a gate not run is never a pass",
                  "a done report that is green because a gate was skipped, or red because its output said FAIL"))
    print("  ok    verify reads the exit code, not the text, and a gate not run is never a pass")


def hook_chain_cases() -> None:
    """install chains a foreign hook instead of refusing, keeps its veto, and uninstall restores it (3.10.0)."""
    enforce = [sys.executable, str(ROOT / "scripts/enforce.py")]
    with tempfile.TemporaryDirectory() as repo:
        def git(*a: str) -> subprocess.CompletedProcess:
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo,
                                  capture_output=True, text=True, timeout=600, check=False)
        git("init", "-q")
        hook = Path(repo) / ".git/hooks/pre-commit"
        foreign = "#!/bin/sh\n[ -f veto ] && exit 7\nexit 0\n"
        hook.write_text(foreign)
        hook.chmod(0o755)
        if subprocess.run([*enforce, "install"], cwd=repo, capture_output=True, timeout=600, check=False).returncode:
            raise SystemExit("FAIL install refused a repository that already had a hook")
        (Path(repo) / "ok.py").write_text("x = 1\n")
        (Path(repo) / "veto").write_text("")
        git("add", "ok.py", "veto")
        if git("commit", "-qm", "vetoed").returncode == 0:
            raise SystemExit("FAIL the chained hook lost the foreign hook's veto")
        git("rm", "-q", "--cached", "veto")
        (Path(repo) / "veto").unlink()
        if git("commit", "-qm", "clean").returncode != 0:
            raise SystemExit("FAIL a clean commit was refused after chaining")
        (Path(repo) / "bad.py").write_text("def broken(:\n")
        git("add", "bad.py")
        if git("commit", "-qm", "broken").returncode == 0:
            raise SystemExit("FAIL the chained hook let a syntax error commit")
        subprocess.run([*enforce, "uninstall"], cwd=repo, capture_output=True, timeout=600, check=False)
        if hook.read_text() != foreign:
            raise SystemExit("FAIL uninstall did not restore the hook install moved aside")
        git("config", "core.hooksPath", ".githooks")
        if subprocess.run([*enforce, "install"], cwd=repo, capture_output=True, timeout=600, check=False).returncode != 1:
            raise SystemExit("FAIL install wrote into a tracked core.hooksPath")
    CASES.append(("install chains an existing hook, keeps its veto, uninstall restores it, a tracked hooksPath is refused",
                  "an installer that refuses every repository that already has a hook, or silently replaces it"))
    print("  ok    install chains an existing hook, keeps its veto, uninstall restores it, a tracked hooksPath is refused")


def declaration_cases() -> None:
    """Each block atlas.yaml declares is read, and each read refuses the shape that block rots into (3.11.0)."""
    plants = [
        ("an issue route naming an undeclared word FAILS", "a typo read as a topic",
         "  memory: [rust, c, cpp, zig, nim, hare, odin]\n", "  memory: [rust, rsut, c, cpp, zig, nim, hare, odin]\n", "names 'rsut'"),
        ("a model route naming a host FAILS", "a host listed as a model",
         "  architecture: [claude, openai_codex]\n", "  architecture: [claude, openai_codex, zed]\n", "a host is not a model"),
        ("a front_end read split on a comma FAILS", "a declaration half missing once loaded",
         '  reads:\n  - "thea-commands/1 (the roster)"\n',
         "  reads: [tools/atlas-output.schema.json (route, gate)]\n  reads_was:\n  - thea-commands/1\n",
         "a flow value split on a comma"),
        ("a drift_review tier split over one FAILS", "hot and cold covering more than the tree",
         "  tiers: {hot: 0.15, cold: 0.15}\n", "  tiers: {hot: 0.95, cold: 0.15}\n", "is not a split of one tree"),
        ("a first_sweep command the CLI lacks FAILS", "an instruction that names a verb nobody answers",
         "clone a release tag and run `python scripts/atlas.py gate <file>`",
         "clone a release tag and run `python scripts/atlas.py gaet <file>`", "does not have"),
        ("a landed state branchstate never reports FAILS", "a vocabulary that describes states no program detects",
         "  landed_states:\n", "  landed_states:\n    shipped: invented\n", "never reports"),
    ]
    for name, kills, old, new, needle in plants:
        with mutated("atlas.yaml", lambda s, o=old, n=new: s.replace(o, n, 1)):
            case(name, kills, True, needle)


def sandbox_cases() -> None:
    """The generated sandbox isolates what the host rows require, and refuses what a flag cannot give (3.12.0)."""
    import json as _json
    import shutil as _shutil

    import sandboxgen
    contract = _json.loads((ROOT / "tools/agent-task.example.json").read_text())
    config = _json.loads(sandboxgen.CONFIG.read_text())
    argv = sandboxgen.docker_argv(contract, config, "/w", "img")
    need = ["--network", "none", "--read-only", "--cap-drop", "ALL", "no-new-privileges", "--pids-limit", "--memory"]
    if any(n not in argv for n in need) or "/w:/work:rw" not in argv or argv[-2:] != ["timeout", "120"]:
        raise SystemExit(f"FAIL the generated docker sandbox is missing a host row: {argv}")
    try:
        sandboxgen.docker_argv({**contract, "network": "allowlist"}, config, "/w", "img")
        raise SystemExit("FAIL a network allowlist was generated as flags, with no egress proxy behind it")
    except SystemExit as refused:
        if "REFUSED" not in str(refused):
            raise
    CASES.append(("the generated sandbox has every host row, and a network allowlist is refused",
                  "host isolation left to a reading of prose, or an allowlist a flag pretends to enforce"))
    print("  ok    the generated sandbox has every host row, and a network allowlist is refused")
    # PROVEN WHERE IT CAN RUN, never counted where it cannot: the case count must not depend on the machine.
    if not _shutil.which("sandbox-exec"):
        print("        macOS sandbox probe: NOT RUN (no sandbox-exec on this machine)")
        return
    with tempfile.TemporaryDirectory() as work:
        profile = Path(work) / "p.sb"
        profile.write_text(sandboxgen.macos_profile(contract, work, str(Path.home())))
        def inside(cmd: str) -> int:
            return subprocess.run(["sandbox-exec", "-f", str(profile), "sh", "-c", cmd], capture_output=True,
                                  timeout=60, check=False).returncode
        probe = Path.home() / ".thea-sandbox-probe"
        results = (inside(f"echo ok > {work}/w"), inside(f"echo x > {probe}"),
                   inside(f"{sys.executable} -c \"import socket; socket.create_connection(('1.1.1.1', 443), 3)\""))
        if results[0] != 0 or results[1] == 0 or results[2] == 0 or probe.exists():
            raise SystemExit(f"FAIL the macOS sandbox did not isolate (worktree, home, network) = {results}")
    print("        macOS sandbox probe: worktree write allowed, home write and network refused")

