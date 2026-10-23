"""The version and closure cases: one plant per declared version site, and the closure rules.

Counted in atlas_test's own CASES. They live here, not in atlas_test.py, because that file is held
to its line ceiling; `run` takes the running module, as cli_test.run does.
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
from pathlib import Path

import atlas


def run(module) -> None:
    _declared_lines_and_counts(module)
    _dependency_document_and_intake_cases(module)
    _gate_listing_case(module)
    _yaml_flow_case(module)
    _yaml_round_trip_case(module)
    _enforce_at_commit_case(module)
    _landing_refuses_red_case(module)
    _staleness_case(module)
    _solo_scorer_case(module)
    _subdependency_case(module)


def _declared_lines_and_counts(module) -> None:
    case, mutated = module.case, module.mutated
    _VERSION = module._VERSION
    """The 2.29.0 cases, split out of main() when it crossed the shape cap: a version read at its
    declared line, not anywhere in the file, and a dependency count that must be the closure."""
    # THE SHAPE THAT SLIPPED THROUGH AT 2.28.0: the declared line is stale while the current version
    # still appears ELSEWHERE in the same file. The old "anywhere in the file" rule passed this.
    _old = ".".join(("0", "0", "1"))
    with mutated(
        "MODEL.md", lambda t, o=_old: t.replace(f"version: {_VERSION}**", f"version: {o}** (was {_VERSION})", 1)
    ):
        case(
            "a stale declared version line FAILS though the file still names VERSION elsewhere",
            "a skew check satisfied by any rendering of the version, such as a generated stamp",
            True,
            "MODEL.md states '0.0.1'",
            by="version_errors",
        )
    with mutated("atlas.yaml", lambda t: t.replace("version_sites:", "version_sites_retired:", 1)):
        case(
            "an empty version-site roster FAILS",
            "a skew check over zero files, which passes forever",
            True,
            "version mismatch: version_sites",
            by="version_errors",
        )


def _dependency_document_and_intake_cases(module) -> None:
    case, mutated = module.case, module.mutated
    # A FALSE MINIMUM (2.28.0): a dependency count typed from direct lines, not the closure an install pulls.
    with mutated("atlas.yaml", lambda t: t.replace("    resolved_closure: 1", "    resolved_closure: 0", 1)):
        case(
            "a dependency count below the locked closure FAILS",
            '"1 dependency" printed while the lock installs more',
            True,
            "the count an install pays is the closure",
            by="inv:dependency_count_is_the_closure",
        )
    with mutated("ABOUT.md", lambda t: t.replace("\n", "\nInstalls in 184 KiB.\n", 1)):
        case(
            "a size typed into an entry document FAILS",
            "a footprint figure true on the day it was typed",
            True,
            "a size typed into prose",
            by="generated_errors",
        )
    with mutated("docs/VERIFY.md", lambda t: t.replace("# ", "# \u200b", 1)):
        case(
            "an invisible character in a tracked file FAILS",
            "an instruction a reviewer cannot see, handed to every model that reads the tree",
            True,
            "carries invisible U+200B",
            by="generated_errors",
        )
    with mutated("docs/VERIFY.md", lambda t: t.replace("# ", "# See `scripts/no_such_instrument.py`. ", 1)):
        case(
            "a backticked path that does not exist FAILS",
            "a mechanism named in prose that nothing implements",
            True,
            "which does not exist",
            by="generated_errors",
        )
    with mutated("atlas.yaml", lambda t: t.replace("  - [unit_tests, tests, focused_tests]\n", "", 1)):
        case(
            "two gates resolving to one command, undeclared, FAIL",
            "race_detection passed by running the unit tests: many gate names, one check",
            True,
            "gate collision",
            by="inv:gates_resolve_distinctly",
        )
    # THE INTAKE LINE IS PLANTED, NOT BORROWED: the first fixture named `intake: 3.0.0`, the second read a
    # live one — both broke when their entry graduated (a_fixture_that_names_what_it_could_read). Every
    # unenforceable entry is a valid host, and one always exists.
    with mutated("atlas.yaml", lambda t: t.replace("    unenforceable:", "    intake: 0.1.0\n    unenforceable:", 1)):
        case(
            "a failure left in intake past two minor versions FAILS",
            "a recorded mistake that never becomes a guard — a promise to come back, kept as an exemption",
            True,
            "has sat in intake since",
            by="inv:failure_modes_name_their_refusal",
        )
    with mutated(
        "scripts/workflowbench.py",
        lambda t: t.replace("text=True, timeout=timeout, check=False", "text=True, check=False", 1),
    ):  # a LITERAL: plantcheck reads it
        case(
            "a subprocess call with no timeout FAILS",
            "a hung tool that ends a run and loses its results",
            True,
            "runs a subprocess with no timeout",
            by="inv:forbidden_calls_are_refused",
        )


def _gate_listing_case(module) -> None:
    CASES = module.CASES
    # `gate <file>` WITH NO GATE: one numbered, runnable line per gate the change needs (3.3.0).
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        _rc = atlas.gate("examples/rust/bounded_retry.rs", None, False)
    _want = len(atlas.required_gates({"change_class": "source_change"}))
    _got = [line for line in _buf.getvalue().splitlines() if line[:1].isdigit()]
    if _rc != 0 or len(_got) != _want:
        raise SystemExit(f"FAIL gate <file> printed {len(_got)} numbered line(s), rc={_rc}; wanted {_want}, rc=0")
    CASES.append(
        (
            "gate <file> with no gate lists every gate the change needs",
            "a first-time user forced to learn the gate vocabulary before getting any answer",
        )
    )
    print("  ok    gate <file> with no gate lists every gate the change needs")


def _yaml_flow_case(module) -> None:
    case, mutated = module.case, module.mutated
    ROOT = module.ROOT
    _quoted = next(
        re.finditer(r"^  root_cause_outside_scope: \{closed_by: '([^']*)'\}$", (ROOT / "atlas.yaml").read_text(), re.M)
    )
    with mutated("atlas.yaml", lambda t, m=_quoted: t.replace(m.group(0), m.group(0).replace("'", ""), 1)):
        case(
            "a YAML flow value split on a comma FAILS",
            "a declaration that loads half its text and passes",
            True,
            "a flow value split on a comma",
            by="parse_errors",
        )


def _yaml_round_trip_case(module) -> None:
    CASES = module.CASES
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
        if _sy(f"k: {_out}", "t").get("k") != _text or _sy(f"k: {{v: {_out}}}", "t").get("k") != {"v": _text}:
            raise SystemExit(f"FAIL yaml_value({_text!r}) -> {_out!r} does not read back")
    CASES.append(
        (
            f"yaml_value round-trips {len(_samples)} hostile strings in plain and flow position",
            "a hand-quoted YAML value that loads as something else, or as half of itself",
        )
    )
    print(f"  ok    yaml_value round-trips {len(_samples)} hostile strings in plain and flow position")


def _enforce_at_commit_case(module) -> None:
    CASES = module.CASES
    ROOT = module.ROOT
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
        _sp.run(
            [sys.executable, str(ROOT / "scripts/enforce.py"), "install"],
            cwd=_repo,
            check=True,
            capture_output=True,
            timeout=600,
        )
        _left = _sp.run(
            ["git", "status", "--porcelain", "--ignored"],
            cwd=_repo,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        ).stdout
        if _left.strip() != "?? bad.py":
            raise SystemExit(f"FAIL enforce install wrote outside the git hook: {_left!r}")
        _sp.run(["git", "add", "bad.py"], cwd=_repo, check=True, timeout=600)
        _commit = _sp.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
            cwd=_repo,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if _commit.returncode == 0:
            raise SystemExit("FAIL the installed pre-commit hook let a syntax error commit")
    CASES.append(
        (
            "enforce refuses a broken file, and its hook blocks the commit",
            "rules an agent can read and skip — a long system prompt with no enforcement behind it",
        )
    )
    print("  ok    enforce refuses a broken file, and its hook blocks the commit")


def _landing_refuses_red_case(module) -> None:
    CASES = module.CASES
    # A LANDING REFUSES A RED CLEAN CHECKOUT (3.4.0): the gate runs in the landing, not in a habit.
    import branchstate

    if branchstate.clean_checkout_errors([[sys.executable, "-c", "raise SystemExit(0)"]]) is not None:
        raise SystemExit("FAIL clean_checkout_errors refused a passing gate")
    if branchstate.clean_checkout_errors([[sys.executable, "-c", "raise SystemExit(3)"]]) is None:
        raise SystemExit("FAIL clean_checkout_errors let a failing gate through")
    CASES.append(
        (
            "a landing refuses when a clean checkout of HEAD fails its gates",
            "a verdict printed and not gated — clean=1 on screen and the lane landed anyway",
        )
    )
    print("  ok    a landing refuses when a clean checkout of HEAD fails its gates")


def _staleness_case(module) -> None:
    CASES = module.CASES
    import staleness

    _out = io.StringIO()
    with contextlib.redirect_stdout(_out):
        staleness.oldest(3)
        staleness.worktrees()
        staleness.review()
    # A SQUASH-MERGED LANE IS FINISHED (3.6.1): commits ahead, tree identical to the base.
    if (
        not staleness.lane_verdict(False, False, 0.0, 0, 1, True).startswith("FINISHED")
        or staleness.lane_verdict(False, False, 0.0, 0, 1, False) != "active"
        or staleness.lane_verdict(True, False, 0.0, 0, 0, True) != "main checkout"
    ):
        raise SystemExit("FAIL staleness called a squash-merged lane active, or a lane with new work finished")
    if any(s not in _out.getvalue() for s in ("main checkout", "least recently edited", "drift review:")):
        raise SystemExit("FAIL staleness did not report the oldest files, or offered the main checkout for removal")
    CASES.append(
        (
            "staleness names the oldest edits and never offers the main checkout for removal",
            "a finished-lane report that tells an agent to delete the main checkout",
        )
    )
    print("  ok    staleness names the oldest edits and never offers the main checkout for removal")


def _solo_scorer_case(module) -> None:
    CASES = module.CASES
    import subprocess as _sp

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
    CASES.append(
        (
            "the solo workflow scorer sees a broken commit, and the hook refuses it",
            "a benchmark reporting 'no difference' because it could not see the difference",
        )
    )
    print("  ok    the solo workflow scorer sees a broken commit, and the hook refuses it")


def _subdependency_case(module) -> None:
    case = module.case
    import importlib.metadata as _md

    _real_requires = _md.requires
    _md.requires = lambda name: ["planted-subdependency>=1"] if name == "pyyaml" else _real_requires(name)
    try:
        case(
            "a sub-dependency the lock does not pin FAILS",
            "an upstream release that quietly grows its own dependencies, read as still one",
            True,
            "the lock does not pin: planted-subdependency",
            by="inv:dependency_count_is_the_closure",
        )
    finally:
        _md.requires = _real_requires
