"""Landing and lifecycle regression groups, split from the general guard suite."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import safeedit

T: Any = None


def run(module):
    global T, ROOT, CASES, case, mutated, atlas, suite_lock
    T = module
    ROOT, CASES, case, mutated, atlas, suite_lock = (
        module.ROOT,
        module.CASES,
        module.case,
        module.mutated,
        module.atlas,
        module.suite_lock,
    )
    landing_target_cases()
    consumer_gate_cases()
    lesson_cases()
    skill_tax_cases()
    rescue_tag_cases()
    declared_input_cases()
    ledger_entry_cases()
    lock_drift_cases()


def landing_target_cases() -> None:
    """A landing acts on the CALLER's repository and reads policy from the atlas (3.41.0)."""
    probe = [sys.executable, "-c", "import atlascore; print(atlascore.worktree())"]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "scripts")}
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as bare:
        subprocess.run(["git", "init", "-q", repo], check=True, timeout=600)
        own = subprocess.run(probe, cwd=repo, capture_output=True, text=True, env=env, timeout=600, check=False)
        none = subprocess.run(probe, cwd=bare, capture_output=True, text=True, env=env, timeout=600, check=False)
        here = subprocess.run(probe, cwd=ROOT, capture_output=True, text=True, env=env, timeout=600, check=False)
        if own.stdout.strip() != str(Path(repo).resolve()):
            raise SystemExit(
                f"FAIL a landing from another repository targets {own.stdout.strip()!r}, not that repository"
            )
        if none.returncode == 0 or "REFUSED" not in none.stderr:
            raise SystemExit("FAIL outside any git repository the landing target fell back instead of refusing")
        if here.stdout.strip() != str(ROOT.resolve()):
            raise SystemExit("FAIL in this checkout the landing target and the atlas are not the same path")
    CASES.append(
        (
            "a landing targets the caller's repository, refuses outside one, and is the atlas only here",
            "an agent using the installed CLI pushing its work into the atlas instead of its own repository",
        )
    )
    print("  ok    a landing targets the caller's repository, refuses outside one, and is the atlas only here")


def consumer_gate_cases() -> None:
    """A consumer's changed file is proven by the gates the atlas routes for it, run in its own tree."""
    import branchstate  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as repo:
        (Path(repo) / "bad.py").write_text("def broken(:\n")
        (Path(repo) / "notes.md").write_text("# notes\n")
        runnable, notes = branchstate.consumer_gates(Path(repo), ["bad.py", "notes.md"], "source_change")
        parse = [argv for argv in runnable if "ast.parse" in " ".join(argv)]
        if not parse:
            raise SystemExit(f"FAIL no routed parse gate for a Python file: {runnable}")
        failed = subprocess.run(parse[0], cwd=repo, capture_output=True, timeout=600, check=False).returncode
        if failed == 0:
            raise SystemExit("FAIL the routed parse gate passed a file that does not parse")
        if not any(n.startswith("notes.md:") for n in notes):
            raise SystemExit("FAIL a route with no declared gate was run or hidden instead of reported")
    CASES.append(
        (
            "a consumer's changed file gets the gates the atlas routes for it, and an undeclared one is reported",
            "an atlas that filters nothing: a consumer's broken file landing because no gate was asked for it",
        )
    )
    print("  ok    a consumer's changed file gets the gates the atlas routes for it, and an undeclared one is reported")


def lesson_cases() -> None:
    """`thea failures --for` hands the shapes relevant to a change, and nothing when none is (3.41.0)."""
    import knowledge  # noqa: PLC0415

    picked = [k for k, _ in knowledge.relevant("failures", "edit a yaml config and write it back", 3)]
    if "a_round_trip_that_drops_what_the_format_allowed" not in picked:
        raise SystemExit(f"FAIL the lesson for a YAML write-back missed the round-trip shape: {picked}")
    if knowledge.relevant("failures", "zzqqxx", 3):
        raise SystemExit("FAIL a query sharing no word with any shape was padded with unrelated lessons")
    CASES.append(
        (
            "a change is handed the ledger shapes that share its words, and an unrelated query gets none",
            "a lesson list that is either the whole ledger or noise, so it teaches nothing at the point of action",
        )
    )
    print("  ok    a change is handed the ledger shapes that share its words, and an unrelated query gets none")


def skill_tax_cases() -> None:
    """A shipped skill's description is bounded, because it is paid on every request (3.24.0)."""
    import re  # noqa: PLC0415

    long_description = "description: " + ("word " * 60)
    with mutated(
        "skills/thea/SKILL.md", lambda s: re.sub(r"^description: .+$", long_description, s, count=1, flags=re.M)
    ):
        case(
            "a shipped skill description over its cap FAILS",
            "a per-turn tax on every session that installs it",
            True,
            "paid on EVERY request",
            by="inv:context_is_progressively_disclosed",
        )
    with mutated("atlas.yaml", lambda s: s.replace("  skill_description_bytes: 155\n", "", 1)):
        case(
            "no declared cap on a shipped skill description FAILS",
            "the only per-turn cost here, bounded by nothing",
            True,
            "declares no skill_description_bytes",
            by="inv:context_is_progressively_disclosed",
        )


def rescue_tag_cases() -> None:
    """A landing tags the tip BEFORE it rebases, so a refused push cannot hide the commit (3.25.0)."""

    def tagged_first() -> bool:
        source = (ROOT / "scripts/branchstate.py").read_text(encoding="utf-8")
        tag_at = source.find('"git", "tag", "-f", rescue')
        rebase_at = source.find('["git", "rebase", f"origin/{base}"]')
        return 0 <= tag_at < rebase_at

    if not tagged_first():
        raise SystemExit("FAIL the rescue tag is missing or runs after the rebase it exists to survive")
    # THE GUARD RUNS INSIDE THE PLANT: this case once only checked that its own replace applied, so it
    # proved the mutation and nothing about the ordering check.
    with mutated(
        "scripts/branchstate.py",
        lambda s: s.replace('subprocess.run(["git", "tag", "-f", rescue]', 'subprocess.run(["git", "status"]', 1),
    ):
        if tagged_first():
            raise SystemExit("FAIL the ordering check passed a landing that never takes the rescue tag")
    CASES.append(
        (
            "a landing tags the lane tip before rebasing, and the tag is taken before the rebase",
            "a push refused after the rebase, leaving the commit reachable only from the reflog",
        )
    )
    print("  ok    a landing tags the lane tip before rebasing, and the tag is taken before the rebase")


def declared_input_cases() -> None:
    """Every input a script reads is declared, and every declared input is read (3.26.0)."""
    # Built at run time: written as a literal, this plant would itself be the undeclared read it plants.
    planted = "THEA_" + "PLANTED_INPUT"
    with mutated("scripts/doctor.py", lambda s, n=planted: s + f'\nimport os\n_probe = os.environ.get("{n}")\n'):
        case(
            "an environment input read by a script and declared nowhere FAILS",
            "a value that is present on one machine and blank on a fresh clone — a wrong answer, not an error",
            True,
            "declared_inputs does not name",
            by="inv:declarations_are_read",
        )
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            "  NO_COLOR: {why:", "  THEA_NOTHING_READS_THIS: {why: x, set_by: x, absent: x}\n  NO_COLOR: {why:", 1
        ),
    ):
        case(
            "a declared input no script reads FAILS",
            "a roster that has stopped describing the tree",
            True,
            "which no script reads",
            by="inv:declarations_are_read",
        )


def ledger_entry_cases() -> None:
    """A ledger entry is written through the emitter (3.49.0): add_entry lands an apostrophe-colon-comma value
    inside its section, above the next key's comment; with the emitter swapped for hand-quoting it REFUSES."""
    import tempfile

    from atlascore import strict_yaml

    path = Path(tempfile.mkdtemp()) / "l.yaml"
    path.write_text("s:\n  a:\n    x: 1\n# owned by t\nt: 2\n", encoding="utf-8")
    want = {"shape": "it's: a, b `c`", "n": 2, "l": ["p", "q"]}
    safeedit.add_entry(path, "s", "b", ["shape=it's: a, b `c`", "n=2", "l=[p,q]"])
    emitter, safeedit.yaml_value = safeedit.yaml_value, lambda v: f"'{v}'"
    try:
        safeedit.add_entry(path, "s", "c", ["shape=it's"])
        refused = False
    except Exception:  # noqa: BLE001 — a parse error and a read-back mismatch are both the refusal
        refused = True
    finally:
        safeedit.yaml_value = emitter
    if (
        strict_yaml(text := path.read_text(encoding="utf-8"), "t") != {"s": {"a": {"x": 1}, "b": want}, "t": 2}
        or "# owned by t" not in text
        or not refused
    ):  # a comment is what a parsed round-trip drops
        raise SystemExit(f"FAIL add_entry: {path.read_text(encoding='utf-8')!r} refused-hand-quoting={refused}")
    CASES.append(
        (
            "a ledger entry written by add_entry reads back, and a hand-quoted one is REFUSED",
            "an apostrophe typed into a quoted ledger value that stops the whole file parsing",
        )
    )
    print("  ok    a ledger entry written by add_entry reads back, and a hand-quoted one is REFUSED")


def lock_drift_cases() -> None:
    """agreement.lock names WHAT moved (3.49.0): one changed section is one finding, a comment-only edit is
    none, and a lock in an older shape is a finding — never the empty diff a clean install prints."""
    import agreement

    ours = agreement.lock_record()
    moved = {**ours, "sections": {**ours["sections"], "version": "0" * 16}}
    old = {"schema": 1, "artifacts": {}}
    found = (agreement.lock_drift(ours, ours), agreement.lock_drift(moved, ours), agreement.lock_drift(old, ours))
    if found[0] or found[1] != ["section/version"] or not found[2]:
        raise SystemExit(f"FAIL lock_drift: identical={found[0]} one-section={found[1]} old-shape={found[2]}")
    CASES.append(
        (
            "lock_drift names the one section that moved, and an old-shape lock is a finding",
            "a whole-file hash that moves on every comment and says nothing about which rule changed",
        )
    )
    print("  ok    lock_drift names the one section that moved, and an old-shape lock is a finding")
