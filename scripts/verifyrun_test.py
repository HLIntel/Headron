#!/usr/bin/env python3
"""Planted cases: verify's runner reads a gate's output bounded, and an exit declared undecided is NOT RUN."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from shutil import rmtree
from threading import Event


def undecided_case(module) -> None:
    """pytest's exit 5 (no tests collected) was a FAIL here and a SKIP in enforce.py: one rule, two verdicts."""
    import verify

    with tempfile.TemporaryDirectory() as scratch:
        # A STAND-IN, NOT pytest: CI installs only the lock, so the case plants the program and its exit.
        stand_in = Path(scratch) / "pytest"
        stand_in.write_text("#!/bin/sh\necho 'no tests ran in 0.00s'\nexit 5\n", encoding="utf-8")
        stand_in.chmod(0o755)
        gate = {"id": "u", "argv": [str(stand_in), "-q"]}
        row = verify.run_gate(gate, Path(scratch))
        if row["verdict"] != "NOT RUN" or "decided nothing" not in row["why"] or row.get("exit") != 5:
            raise SystemExit(f"FAIL verify read pytest's no-tests exit as {row['verdict']}: {row.get('why')!r}")
        real = verify.undecided_exit
        verify.undecided_exit = lambda tool, code: ""
        try:
            planted = verify.run_gate(gate, Path(scratch))
        finally:
            verify.undecided_exit = real
    if planted["verdict"] != "FAIL":
        raise SystemExit("FAIL the undecided case did not notice a runner that ignores enforcement/undecided_exits")
    if verify.verdict_code([row]) != 2:
        raise SystemExit("FAIL an undecided gate did not hold verify at exit 2 (incomplete is not done)")
    module.CASES.append(
        (
            "a gate exit declared undecided is NOT RUN in verify, as it is in enforce",
            "a consumer with no tests yet reading FAIL, blamed on a change that decided nothing",
        )
    )
    print("  ok    pytest's no-tests exit is NOT RUN in verify, as in enforce")


def bounded_case(module) -> None:
    """A gate printing past HEAD_BYTES + TAIL_BYTES is read as head and tail; its byte count is still true."""
    import verify

    flood = "import sys; sys.stdout.write('SCOPE head\\n' + 'x' * 999 + '\\n'); [print('y' * 99) for _ in range(9000)]; print('FAIL the tail'); raise SystemExit(1)"
    row = verify.run_gate({"id": "f", "argv": ["python", "-c", flood]})
    if row["verdict"] != "FAIL" or "the tail" not in row["why"] or row["output_bytes"] < 900_000:
        raise SystemExit(
            f"FAIL a flooding gate was misread: {row['verdict']} {row.get('why')!r} {row.get('output_bytes')}"
        )
    _, read, size = verify._bounded_run([sys.executable, "-c", flood], Path.cwd())
    if len(read) > verify.HEAD_BYTES + verify.TAIL_BYTES + 200 or size < 900_000:
        raise SystemExit(f"FAIL verify held {len(read)} of {size} bytes of a flooding gate, not a head and a tail")
    if "SCOPE head" not in row["self_report"]:
        raise SystemExit("FAIL the head of a flooding gate's output, where its self-report is, was dropped")
    module.CASES.append(
        (
            "a gate's output is read as a bounded head and tail, its verdict line and self-report kept",
            "a looping gate's output held whole in memory until the machine kills the run",
        )
    )
    print("  ok    a flooding gate is read bounded: head, tail and true byte count")


def concurrency_case(module) -> None:
    """Readers overlap, while a mutator begins only after the last reader exits."""
    import verify

    readers = [
        {"id": "reader-a", "argv": ["python", "-c", ""], "mutates": False},
        {"id": "reader-b", "argv": ["python", "-c", ""], "mutates": False},
    ]
    mutator = {"id": "plant", "argv": ["python", "-c", ""], "mutates": True}
    events: list[tuple[str, float]] = []
    real = verify.run_gate

    def planted(gate, cwd, env=None):
        events.append((f"start:{gate['id']}", time.monotonic()))
        Event().wait(0.2)
        events.append((f"end:{gate['id']}", time.monotonic()))
        return {"id": gate["id"], "verdict": "PASS", "argv": gate["argv"]}

    verify.run_gate = planted
    streamed: list[dict] = []
    try:
        rows = verify.run_declared_gates([*readers, mutator], Path.cwd(), jobs=2, on_row=streamed.append)
    finally:
        verify.run_gate = real
    moments = dict(events)
    if moments["start:reader-a"] >= moments["end:reader-b"] or moments["start:reader-b"] >= moments["end:reader-a"]:
        raise SystemExit("FAIL read-only gates did not overlap")
    if moments["start:plant"] < max(moments["end:reader-a"], moments["end:reader-b"]):
        raise SystemExit("FAIL mutating gate began before all read-only gates ended")
    if [row["id"] for row in rows] != ["reader-a", "reader-b", "plant"]:
        raise SystemExit("FAIL concurrent gates lost declared result order")
    if len(streamed) != 3 or {r["id"] for r in streamed} != {"reader-a", "reader-b", "plant"}:
        raise SystemExit(f"FAIL streamed telemetry rows lost verdicts: {streamed!r}")
    from testgroups import micro_shreds

    shredded = micro_shreds(["g1", "g2", "g3", "g4"], 1, 2)
    if shredded != ["g2", "g4"]:
        raise SystemExit(f"FAIL micro_shreds partition incorrect: {shredded!r}")
    module.CASES.append(
        (
            "read-only verification gates overlap, while mutating gates wait and results retain declaration order",
            "a planted suite reads a concurrently-mutated tree or a parallel runner scrambles gate attribution",
        )
    )
    print("  ok    read-only gates overlap; the mutating gate waits and result order is stable")


def artifact_gate_home_case(module) -> None:
    """A per-artifact gate id is a record key, not a temporary-directory name."""
    import verify

    environment = verify._gate_env("0-compiler_or_typechecker:scripts/atlas.py")
    home = Path(environment["HEADRON_HOME"])
    try:
        if not home.is_dir() or ":" in home.name or "/" in home.name:
            raise SystemExit(f"FAIL a per-artifact gate made an invalid private home: {home}")
    finally:
        rmtree(home, ignore_errors=True)
    module.CASES.append(
        (
            "a per-artifact gate id becomes a portable private verifier home",
            "a changed-file verification aborting before a gate can report its verdict on macOS",
        )
    )
    print("  ok    a per-artifact gate id makes a portable private verifier home")


def dependency_pruning_case(module) -> None:
    """A failed prerequisite prevents only its descendants from starting, never hides them."""
    import verify

    gates = [
        {"id": "contract", "argv": ["python", "-c", ""], "mutates": False},
        {"id": "dependent", "argv": ["python", "-c", ""], "mutates": False, "depends_on": ["contract"]},
        {"id": "independent", "argv": ["python", "-c", ""], "mutates": False},
    ]
    called: list[str] = []
    real = verify.run_gate

    def planted(gate, cwd, env=None):
        called.append(gate["id"])
        verdict = "FAIL" if gate["id"] == "contract" else "PASS"
        return {"id": gate["id"], "argv": gate["argv"], "verdict": verdict}

    verify.run_gate = planted
    try:
        rows = verify.run_declared_gates(gates, Path.cwd(), jobs=2)
    finally:
        verify.run_gate = real
    if called.count("contract") != 1 or "dependent" in called or "independent" not in called:
        raise SystemExit(f"FAIL verify did not prune only the failed gate's descendant: {called!r}")
    dependent = next(row for row in rows if row["id"] == "dependent")
    if dependent["verdict"] != "NOT RUN" or dependent["why"] != "pruned: prerequisite contract was FAIL":
        raise SystemExit(f"FAIL pruned gate was not an explicit NOT RUN row: {dependent!r}")
    reused = {"contract": {"id": "contract", "argv": gates[0]["argv"], "verdict": "REUSED"}}
    verify.run_gate = planted
    try:
        resumed = verify.run_declared_gates(gates, Path.cwd(), jobs=2, completed=reused)
    finally:
        verify.run_gate = real
    if next(row for row in resumed if row["id"] == "dependent")["verdict"] != "PASS":
        raise SystemExit("FAIL a reused prerequisite did not release its dependent gate")
    cyclic = [{"id": "a", "argv": [], "depends_on": ["b"]}, {"id": "b", "argv": [], "depends_on": ["a"]}]
    try:
        verify.gate_dependencies(cyclic)
    except ValueError:
        pass
    else:
        raise SystemExit("FAIL verify accepted a cyclic gate dependency graph")
    module.CASES.append(
        (
            "a gate whose declared prerequisite fails is NOT RUN and never spawned, while unrelated gates still run or reuse",
            "a failed contract starting every expensive downstream gate or silently omitting it from the verdict",
        )
    )
    print("  ok    failed prerequisites prune descendants and preserve explicit NOT RUN rows")


def proof_scope_case(module) -> None:
    """A proof measures its declared path and gates, never the caller's unrelated dirty diff."""
    import copy

    import agentpolicy
    import atlas
    import atlascore
    import declcheck
    import verify

    path = "scripts/doctor.py"
    planned = agentpolicy.required_gates(
        {"change_class": "security_sensitive", "risk_modifiers": [], "task_profile": "implementation"}
    )
    security = atlas.plan_record(path, "python", "security", "source_change", [])
    security_proof, _ = atlascore.proof_record(path, "security", "source_change", [], False)
    required = {"codeql", "authorization_tests", "no_plaintext_at_rest_check"}
    if security["tools"] != ["security"] or not required <= set(security["required_gates"]):
        raise SystemExit(f"FAIL security plan omitted task tools or gates: {security}")
    if security_proof is None or security_proof["required_gates"] != security["required_gates"]:
        raise SystemExit("FAIL proof and plan disagree about the security task floor")
    data = copy.deepcopy(atlas.atlas())
    data["task_profiles"]["security"]["gates"] = 7
    original = declcheck.atlas
    declcheck.atlas = lambda: data
    try:
        if not any("security/gates has an invalid type" in error for error in declcheck.task_profile_errors()):
            raise SystemExit("FAIL malformed task profile gates were not refused")
    finally:
        declcheck.atlas = original
    planned_record, planned_code = atlascore.proof_record(path, "implementation", "security_sensitive", [], False)
    if (
        planned_code != 2
        or planned_record is None
        or planned_record["verdict"] != "NOT RUN"
        or planned_record["verification"]["exit"] != 2
    ):
        raise SystemExit(f"FAIL planned proof was success-shaped: code={planned_code}, record={planned_record}")
    planned_rows = planned_record["verification"]["rows"]
    if [row["id"] for row in planned_rows] != planned or any(
        "state" not in row or "argv" not in row for row in planned_rows
    ):
        raise SystemExit(f"FAIL planned proof omitted its code-derived exit plan: {planned_record}")
    seen: list[dict] = []
    real = verify.run_declared_gates

    def planted(gates, cwd, jobs):
        seen.extend(gates)
        return [{"id": gate["id"], "verdict": "PASS", "why": "", "argv": gate["argv"]} for gate in gates]

    verify.run_declared_gates = planted
    try:
        measured, code = atlascore.proof_record(path, "implementation", "security_sensitive", [], True)
    finally:
        verify.run_declared_gates = real
    if measured is None:
        raise SystemExit("FAIL measured proof returned no record")
    runnable = [gate for gate in planned if atlas.gate_record(path, gate)["state"] == "runnable"]
    if [gate["id"] for gate in seen] != runnable:
        raise SystemExit(f"FAIL proof ran {seen!r}, not declared runnable gates {runnable!r}")
    if measured["required_gates"] != planned or [row["id"] for row in measured["verification"]["rows"]] != planned:
        raise SystemExit(f"FAIL proof record dropped planned gates: {measured}")
    if code != 2 or measured["verdict"] != "NOT RUN":
        raise SystemExit(f"FAIL absent declared gates became a passing proof: code={code}, record={measured}")
    module.CASES.append(
        (
            "a proof instantly exposes its code-derived exit plan, measures only its requested artifact's gates, and planned or absent evidence exits non-successfully",
            "a security-sensitive proof passing after `verify --changed` ran another file's fast loop or skipped a required gate",
        )
    )
    print("  ok    proof: requested gates and artifact measured; planned or absent evidence is non-success")


def resume_binding_case(module) -> None:
    import contextlib
    import io
    import json
    from types import SimpleNamespace
    from unittest.mock import patch

    import knowledge

    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        marker = root / "headron-last-verify.json"
        for digest, code, expected in [
            ("old", 0, "verify"),
            (None, 0, "verify"),
            ("current", 1, "verify"),
            ("current", 0, "commit"),
        ]:
            marker.write_text(json.dumps({"exit": code, "rows": [], "input_digest": digest}))

            def git(root, *args):
                return SimpleNamespace(
                    stdout=" M file\n" if args[0] == "status" else "0 0" if args[0] == "rev-list" else "branch"
                )

            output = io.StringIO()
            with (
                patch.object(knowledge, "ROOT", root),
                patch.object(knowledge, "git_run", git),
                patch("safeedit._git_path", side_effect=lambda name: root / name),
                patch("safeedit.plant_leftovers", return_value=[]),
                patch("hostshape.read_journal", return_value=([], [])),
                patch("hostshape.unverified_steps", return_value=[]),
                patch("verify.input_digest", return_value="current"),
                contextlib.redirect_stdout(output),
            ):
                knowledge.resume(True)
            if expected not in json.loads(output.getvalue())["next"]:
                raise SystemExit(f"FAIL resume accepted verification: digest={digest}, exit={code}")
    module.CASES.append(("resume binds verification to the current tree", "stale verification recommends committing"))
    print("  ok    resume requires current passing verification")


def history_never_decides_case(module) -> None:
    """A recorded verdict never stands in for a run: only a PASS on this exact scope is reused, and what
    learn() draws from the past changes neither a verdict nor the exit code."""
    import verify

    gate = {"id": "contract", "argv": ["python", "scripts/atlas.py", "check"], "mutates": False}
    with tempfile.TemporaryDirectory() as scratch:
        store, real_store = Path(scratch) / "evidence.json", verify._evidence_path
        verify._evidence_path = lambda: store
        try:
            key, scope = verify.gate_key(gate), verify.proof_scope(gate, "tree")
            for told in ("FAIL", "NOT RUN", "REUSED"):
                verify.write_evidence({key: gate | {"verdict": told, "scope": scope}})
                if verify.reuse_evidence([gate], "tree"):
                    raise SystemExit(f"FAIL a recorded {told} row was reused as proof; only a PASS may be")
            verify.write_evidence({key: gate | {"verdict": "PASS", "scope": scope}})
            if not verify.reuse_evidence([gate], "tree") or verify.reuse_evidence([gate], "moved"):
                raise SystemExit("FAIL a PASS was not reused on its scope, or was reused off it")
        finally:
            verify._evidence_path = real_store
        import safeedit

        lessons, real_git_path = Path(scratch) / "lessons.json", safeedit._git_path
        safeedit._git_path = lambda name: lessons
        rows = [{"id": "a", "verdict": "PASS"}, {"id": "b", "verdict": "FAIL", "why": "seen before"}]
        frozen, before = str(rows), verify.verdict_code(rows)
        try:
            for _ in range(3):  # the third sighting is a recurring cause: still advice, never a verdict
                verify.learn(rows)
        finally:
            safeedit._git_path = real_git_path
        if str(rows) != frozen or verify.verdict_code(rows) != before or not lessons.is_file():
            raise SystemExit("FAIL learn() changed a verdict or the exit code, or recorded nothing")
    module.CASES.append(("a recorded verdict never decides a gate", "a past FAIL or a lesson deciding this run"))
    print("  ok    only a PASS on this scope is reused, and lessons never change a verdict")


def key_sees_declared_env_case(module) -> None:
    """A declared variable re-measures; the session id and suite pid differ every run, so reading them
    would end reuse. ATLAS_SHARD runs half the suite, and half's PASS must not stand for the whole."""
    import os

    import verify

    gate = {"id": "suite", "argv": ["python", "suite.py"], "mutates": True, "env": ["ATLAS_SHARD"]}
    names = ("ATLAS_SHARD", "CLAUDE_CODE_SESSION_ID", "HEADRON_SUITE_PID", "HEADRON_HOME")
    saved = {name: os.environ.get(name) for name in names}
    try:
        os.environ.pop("ATLAS_SHARD", None)
        whole = verify.gate_key(gate)
        os.environ["ATLAS_SHARD"] = "core"
        half = verify.gate_key(gate)
        os.environ.update(CLAUDE_CODE_SESSION_ID="one", HEADRON_SUITE_PID="1", HEADRON_HOME="/run/one")
        first = verify.gate_key(gate)
        os.environ.update(CLAUDE_CODE_SESSION_ID="two", HEADRON_SUITE_PID="2", HEADRON_HOME="/run/two")
        second = verify.gate_key(gate)
    finally:
        for name, value in saved.items():
            os.environ.pop(name, None) if value is None else os.environ.update({name: value})
    if whole == half or first != second:
        raise SystemExit(f"FAIL gate_key: declared var moved it={whole != half}, per-run var held it={first == second}")
    module.CASES.append(
        ("a declared variable moves the key and a per-run one does not", "half a suite reused as whole")
    )
    print("  ok    the evidence key reads declared variables and no others")


def key_names_running_interpreter_case(module) -> None:
    """run_gate runs "python" as sys.executable, so that is the program whose identity counts, and two venvs
    on one base interpreter are told apart by sys.prefix."""
    import verify

    gate = {"id": "g", "argv": ["python", "g.py"], "mutates": False}
    asked: list[str] = []
    real_identity, real_prefix = verify._program_identity, verify.sys.prefix
    try:
        verify._program_identity = lambda name: asked.append(name) or "seen"
        here = verify.gate_key(gate)
        verify.sys.prefix = "/another/venv"
        there = verify.gate_key(gate)
    finally:
        verify._program_identity, verify.sys.prefix = real_identity, real_prefix
    if set(asked) != {verify.sys.executable} or here == there:
        raise SystemExit(f"FAIL gate_key asked about {asked}, venv told apart={here != there}")
    module.CASES.append(("the key names the interpreter that runs the gate", "a PASS from another venv reused here"))
    print("  ok    the evidence key names the running interpreter and its venv")


def run(module) -> None:
    for case in [
        undecided_case,
        bounded_case,
        concurrency_case,
        artifact_gate_home_case,
        dependency_pruning_case,
        proof_scope_case,
        resume_binding_case,
        history_never_decides_case,
        key_sees_declared_env_case,
        key_names_running_interpreter_case,
    ]:
        case(module)


run_verify_tests = run


if __name__ == "__main__":
    import types

    run_verify_tests(types.SimpleNamespace(CASES=[]))
    print("verifyrun tests: pass")
