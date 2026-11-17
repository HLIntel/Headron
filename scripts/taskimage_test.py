"""Planted task-image cases (scripts/taskimage.py). Loaded by atlas_guards_test; each plants the defect an image
could hide: a resume against a contract the image was not recorded for, a node with no result read as a pass, a
dry run read as a pass, a stale pass reused without identifying external inputs, a private path or token written into a pushable
ref, and two writers overwriting one another's checkpoint.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "tools" / "agent-task.example.headron"


def _git(repo: Path, *args: str) -> str:
    import taskimage  # noqa: PLC0415

    return taskimage._git(repo, *args)  # noqa: SLF001


def _repo(top: Path) -> Path:
    repo = top / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "a.txt")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "seed")
    return repo


def _refused(call: Callable[[], object]) -> str:
    import taskimage  # noqa: PLC0415

    try:
        call()
    except taskimage.Refused as why:
        return str(why)
    return ""


def _record(contract: dict, states: dict[str, tuple[bool, int]]) -> dict:
    rows = [{"gate": g, "ran": ran, "exit_code": code, "command": g} for g, (ran, code) in states.items()]
    status = "verified" if all(ran and code == 0 for ran, code in states.values()) else "controls_verified"
    return {**contract, "outcome": {"status": status, "gates": rows, "receipt": {"contract": "x", "base": None}}}


def _cases(top: Path) -> list[tuple[str, str, bool, object]]:
    import agentpolicy  # noqa: PLC0415
    import agentrun  # noqa: PLC0415
    import headronlang  # noqa: PLC0415
    import taskimage  # noqa: PLC0415

    repo = _repo(top)
    contract = headronlang.load_contract(EXAMPLE)
    task = str(contract["task_id"])
    gates = [str(g) for g in agentpolicy.required_gates(contract)]

    def run_image(path: Path, execute: bool, resume: bool = False, repo: Path = repo) -> tuple[dict, int]:
        with mock.patch.object(taskimage, "ROOT", repo):
            return taskimage.run_image(path, execute, resume=resume, repo=repo)

    wrong_repo = _refused(lambda: taskimage.run_image(EXAMPLE, False, False, repo))

    # Resume refuses a contract the image was not recorded for, and never reaches the runner.
    taskimage.compile_image(EXAMPLE, repo)
    changed = top / "changed.headron"
    changed.write_text(EXAMPLE.read_text().replace('objective "', 'objective "Changed. ', 1))
    with mock.patch.object(agentrun, "execute_contract", side_effect=AssertionError("ran")) as runner:
        stale = _refused(lambda: run_image(changed, False, resume=True, repo=repo))
        stale_ran = runner.called

    # A run records each node; a dry-run row and a missing node read NOT RUN, never PASS.
    first = {g: (i == 0, 0) for i, g in enumerate(gates)}
    with mock.patch.object(agentrun, "execute_contract", return_value=(_record(contract, first), 1)):
        run_image(EXAMPLE, False, resume=False, repo=repo)
    view, inspect_code = taskimage.inspect(task, repo)
    states = {name: node["state"] for name, node in view["nodes"].items()}
    commit, files = taskimage.read(task, repo) or ("", {})
    state = json.loads(files["state.json"])
    state["nodes"] = {gates[0]: state["nodes"][gates[0]]}
    missing = dict(taskimage.nodes_of(state))
    refused_state = {**state, "status": "refused", "nodes": {g: {"state": "PASS"} for g in gates}}
    with mock.patch.object(
        taskimage, "read", return_value=(commit, {"state.json": json.dumps(refused_state).encode()})
    ):
        _, refused_code = taskimage.inspect(task, repo)

    # A matching tree cannot prove external inputs unchanged; resume must not reuse a pass.
    with mock.patch.object(agentrun, "execute_contract", return_value=(_record(contract, first), 1)) as runner:
        run_image(EXAMPLE, False, resume=True, repo=repo)
        runner_args = runner.call_args.args
    rows = agentrun.run_gates(contract, top / "audit.jsonl", False, {})
    every = [{**r, "ran": False, "reused": True, "exit_code": 0} for r in rows]
    verdicts = (agentrun.run_status(rows, []), agentrun.run_status(every, []), agentrun.run_status([], []))
    after, _ = taskimage.inspect(task, repo)

    # A successful runner must not publish a verified image for dirty, unknown, or changed source.
    passed_record = _record(contract, dict.fromkeys(gates, (True, 0)))
    import obligations  # noqa: PLC0415

    tree_refusals = []
    for identities in (("tree+dirty",), (obligations.UNKNOWN_TREE,), ("tree-a", "tree-b")):
        with (
            mock.patch.object(obligations, "tree", side_effect=identities),
            mock.patch.object(agentrun, "execute_contract", return_value=(passed_record, 0)),
        ):
            tree_refusals.append(_refused(lambda: run_image(EXAMPLE, True, False, repo)))

    # A verified claim needs the exact planned gates, full outcome and matching receipt and tree.
    head = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    outcome = passed_record["outcome"]
    outcome.update(
        {"mode": "full", "denials": [], "receipt": agentpolicy.receipt({**contract, "status": "verified"}, None, head)}
    )
    good_files = taskimage.image_files(contract, outcome["gates"], outcome, tree)
    good_state = json.loads(good_files["state.json"])
    valid = taskimage.verified_image(task, good_state, good_files, repo)
    forged = []
    for name in ("contract.json", "outcome.json", "receipt.json"):
        forged.append(
            taskimage.verified_image(task, good_state, {k: v for k, v in good_files.items() if k != name}, repo)
        )
    bad_state = {**good_state, "order": ["invented"], "nodes": {"invented": {"state": "PASS"}}}
    forged.append(taskimage.verified_image(task, bad_state, good_files, repo))
    bad_receipt = {**good_files, "receipt.json": b"{}"}
    forged.append(taskimage.verified_image(task, good_state, bad_receipt, repo))
    with mock.patch.object(taskimage, "read", return_value=(commit, good_files)):
        claimed, claimed_code = taskimage.inspect(task, repo)
    with mock.patch.object(taskimage, "read", return_value=(commit, {"state.json": json.dumps(bad_state).encode()})):
        invented, invented_code = taskimage.inspect(task, repo)

    # A private path in the contract is never written; the escape comment does not opt it out.
    leaky = top / "leaky.headron"
    home = "/" + "Users/alice/notes"
    leaky.write_text(EXAMPLE.read_text().replace('objective "', f'objective "{home} privacy: allow ', 1))
    leak = _refused(lambda: taskimage.compile_image(leaky, repo))
    leak_head = _git(repo, "rev-parse", taskimage.PREFIX + task)
    token = top / "token.headron"
    token.write_text(EXAMPLE.read_text().replace('objective "', 'objective "' + "gh" + "p_" + "A" * 36 + " ", 1))
    secret = _refused(lambda: taskimage.compile_image(token, repo))

    # Another writer's checkpoint is not overwritten: a write expecting an older commit is refused.
    lost = _refused(lambda: taskimage.write(task, {"x": b"y\n"}, "task x: compile", None, repo))
    digest = _refused(lambda: taskimage.write(task, {"x": b"y\n"}, "task x " + "ab" * 32, commit, repo))
    _git(repo, "rm", "-q", "a.txt")
    unread, _ = taskimage.inspect(task, repo)

    return [
        (
            "task image refuses mismatched execution roots and incomplete verified claims",
            "a verified image with invented gates or missing evidence, or gates run in a different repository",
            "runner's repository" in wrong_repo
            and valid
            and not any(forged)
            and claimed_code == invented_code == 1
            and claimed["record_consistent"]
            and not invented["record_consistent"],
            (wrong_repo, valid, forged, claimed_code, invented_code),
        ),
        (
            "task resume refuses an image recorded for another contract, before any gate runs",
            "a resume that continues a task's checkpoints under a contract that was edited since they were taken",
            "stale contract" in stale and not stale_ran,
            (stale, stale_ran),
        ),
        (
            "a task image reads a dry-run gate and a node with no recorded result as NOT RUN, never PASS",
            "an image that reports a gate as passed because nothing recorded it failing",
            states[gates[0]] == "PASS"
            and all(states[g] == taskimage.NOT_RUN for g in gates[1:])
            and inspect_code == 1
            and refused_code == 1
            and all(missing[g]["state"] == taskimage.NOT_RUN for g in gates[1:])
            and taskimage.node_state({"ran": False, "exit_code": 0}) == taskimage.NOT_RUN,
            (states, inspect_code, missing),
        ),
        (
            "task resume does not reuse a pass, and checkpoints stack on the ref",
            "a pass carried forward without identifying external inputs",
            len(runner_args) == 2
            and [taskimage.node_state(r) for r in rows] == [taskimage.NOT_RUN] * len(gates)
            and verdicts == ("controls_verified", "controls_verified", "controls_verified")
            and all("clean source tree" in reason for reason in tree_refusals)
            and after["checkpoints"] == 3,
            (runner_args, verdicts, after["checkpoints"]),
        ),
        (
            "a task image refuses a home path, a token, a full digest, and a ref another writer moved",
            "a pushable ref that publishes a private path or a secret, or two runs silently overwriting one another",
            "home path" in leak
            and "privacy_guard" in secret
            and leak_head == after["commit"]
            and "update-ref" in lost
            and "digest" in digest,
            (leak, secret, lost, digest),
        ),
        (
            "task inspect reads the ref alone, with the working tree gone",
            "an inspect that re-derives the image from files the ref was meant to replace",
            unread["commit"] == after["commit"] and unread["nodes"] == after["nodes"],
            unread["commit"],
        ),
    ]


def run(module: ModuleType) -> None:
    with (
        tempfile.TemporaryDirectory(prefix="headron-taskimage-") as tmp,
        mock.patch.dict(os.environ, {"HEADRON_HOME": str(Path(tmp) / "home")}),
    ):
        cases = _cases(Path(tmp))
    for name, kills, ok, got in cases:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  got: {got!r}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")
