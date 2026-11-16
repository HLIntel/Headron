"""Planted task-image cases (scripts/taskimage.py). Loaded by atlas_guards_test; each plants the defect an image
could hide: a resume against a contract the image was not recorded for, a node with no result read as a pass, a
dry run read as a pass, a pass reused on a dirty or different tree, a private path written into a pushable ref,
and two writers overwriting one another's checkpoint.
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
    import obligations  # noqa: PLC0415
    import taskimage  # noqa: PLC0415

    repo = _repo(top)
    contract = headronlang.load_contract(EXAMPLE)
    task = str(contract["task_id"])
    gates = [str(g) for g in agentpolicy.required_gates(contract)]
    tree = obligations.tree(repo)

    # Resume refuses a contract the image was not recorded for, and never reaches the runner.
    taskimage.compile_image(EXAMPLE, repo)
    changed = top / "changed.headron"
    changed.write_text(EXAMPLE.read_text().replace('objective "', 'objective "Changed. ', 1))
    with mock.patch.object(agentrun, "execute_contract", side_effect=AssertionError("ran")) as runner:
        stale = _refused(lambda: taskimage.run_image(changed, False, resume=True, repo=repo))
        stale_ran = runner.called

    # A run records each node; a dry-run row and a missing node read NOT RUN, never PASS.
    first = {g: (i == 0, 0) for i, g in enumerate(gates)}
    with mock.patch.object(agentrun, "execute_contract", return_value=(_record(contract, first), 1)):
        taskimage.run_image(EXAMPLE, False, resume=False, repo=repo)
    view, inspect_code = taskimage.inspect(task, repo)
    states = {name: node["state"] for name, node in view["nodes"].items()}
    commit, files = taskimage.read(task, repo) or ("", {})
    state = json.loads(files["state.json"])
    state["nodes"] = {gates[0]: state["nodes"][gates[0]]}
    missing = dict(taskimage.nodes_of(state))

    # Resume reuses only what passed on this clean tree, and passes that set to agentrun.
    with mock.patch.object(agentrun, "execute_contract", return_value=(_record(contract, first), 1)) as runner:
        taskimage.run_image(EXAMPLE, False, resume=True, repo=repo)
        reused_arg = runner.call_args.args[2]
    rows = agentrun.run_gates(contract, top / "audit.jsonl", False, {}, frozenset({gates[0]}))
    after, _ = taskimage.inspect(task, repo)
    passed = {"tree": tree, "order": gates, "nodes": {gates[0]: {"state": "PASS"}}}

    # A private path in the contract is never written; the escape comment does not opt it out.
    leaky = top / "leaky.headron"
    home = "/" + "Users/alice/notes"
    leaky.write_text(EXAMPLE.read_text().replace('objective "', f'objective "{home} privacy: allow ', 1))
    leak = _refused(lambda: taskimage.compile_image(leaky, repo))
    leak_head = _git(repo, "rev-parse", taskimage.PREFIX + task)

    # Another writer's checkpoint is not overwritten: a write expecting an older commit is refused.
    lost = _refused(lambda: taskimage.write(task, {"x": b"y\n"}, "task x: compile", None, repo))
    digest = _refused(lambda: taskimage.write(task, {"x": b"y\n"}, "task x " + "ab" * 32, commit, repo))
    _git(repo, "rm", "-q", "a.txt")
    unread, _ = taskimage.inspect(task, repo)

    return [
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
            and all(missing[g]["state"] == taskimage.NOT_RUN for g in gates[1:])
            and taskimage.node_state({"ran": False, "exit_code": 0}) == taskimage.NOT_RUN,
            (states, inspect_code, missing),
        ),
        (
            "task resume reuses a pass only on the same clean tree, and checkpoints stack on the ref",
            "a pass from another commit or from uncommitted changes carried forward as if it covered this tree",
            reused_arg == frozenset({gates[0]})
            and [taskimage.node_state(r) for r in rows] == ["REUSED"] + [taskimage.NOT_RUN] * (len(gates) - 1)
            and taskimage.reusable(passed, tree + "+dirty") == frozenset()
            and taskimage.reusable({**passed, "tree": tree + "+dirty"}, tree + "+dirty") == frozenset()
            and taskimage.reusable(passed, "other") == frozenset()
            and after["checkpoints"] == 3,
            (reused_arg, after["checkpoints"]),
        ),
        (
            "a task image refuses a home path, a full digest in its message, and a ref another writer moved",
            "a pushable ref that publishes a private path, or two runs silently overwriting one another",
            "home path" in leak and leak_head == after["commit"] and "update-ref" in lost and "digest" in digest,
            (leak, lost, digest),
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
