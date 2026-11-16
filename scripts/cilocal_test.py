#!/usr/bin/env python3
"""Headron's native CI through its public CLI: planted pipelines, run as a real graph, observed by what ran."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import ci
import cidrift
import cilocal
import cipipeline
import micrograph
from cipipeline import Job, Step
from micrograph import Node
from microprogram import MicroResult
from seats_test import _case

ROOT = Path(__file__).resolve().parents[1]

# A PLANTED DECLARATION: the real Job and Step types, three contract jobs (one sharded), and three that must
# never read as a pass: a hung step, a missing tool, a step only a hosted runner can answer.
PIPELINE = '''
from cipipeline import Job, Step

CONTRACT = ("first", "pair", "join")
JOBS = (
    Job("first", "atlas", 30, (Step("see the tree", """cat dirty.txt >> "$SHARED/dirty" || true
case "${PLANT:-}" in first) exit 3 ;; kill) kill -9 $PPID; sleep 5 ;; esac""", 20),)),
    Job("pair", "atlas", 30, (Step("meet the other shard", """echo "start $HEADRON_CI_SHARD"
touch "mine-$HEADRON_CI_SHARD" "$SHARED/$HEADRON_CI_SHARD"
MEET
[ "$(ls mine-*)" = "mine-$HEADRON_CI_SHARD" ] || exit 8
rm "mine-$HEADRON_CI_SHARD"
echo "$HEADRON_CI_SHARD" > "$HEADRON_CI_ARTIFACTS/edge-$HEADRON_CI_SHARD"
echo "end $HEADRON_CI_SHARD"
""", 20),), needs=("first",), shards=("a", "b")),
    Job("join", "atlas", 30, (Step("union", 'cat "$HEADRON_CI_ARTIFACTS"/edge-* > "$SHARED/union"', 20),), needs=("pair",)),
    Job("slow", "extra", 5, (Step("hang", "sleep 30", 1),)),
    Job("toolless", "extra", 10, (Step("need a tool", "touch \\"$SHARED/ran\\"", 5, tools=("no-such-tool-zq",)),)),
    Job("hosted", "extra", 10, (Step("attest", "touch \\"$SHARED/ran\\"", 5, unavailable="a hosted runner's OIDC token"),)),
)
'''
TOGETHER = """for _ in $(seq 100); do [ -e "$SHARED/a" ] && [ -e "$SHARED/b" ] && break; sleep 0.1; done; [ -e "$SHARED/a" ] && [ -e "$SHARED/b" ] || exit 9"""  # noqa: E501
ALONE = 'mkdir "$SHARED/busy" || exit 7; sleep 0.5; rmdir "$SHARED/busy"'


def _repo(base: Path, name: str, meet: str = TOGETHER) -> tuple[Path, Path]:
    """A committed repository whose ci-local.sh is the real runner, as a fanned-out child runs it."""
    repo, shared = base / name, base / f"{name}-shared"
    (repo / ".github").mkdir(parents=True)
    (repo / "scripts").mkdir()
    shared.mkdir()
    (repo / "scripts" / "cipipeline.py").write_text(PIPELINE.replace("MEET", meet), encoding="utf-8")
    script = repo / ".github" / "ci-local.sh"
    script.write_text(
        '#!/bin/bash\ncd "$(git rev-parse --show-toplevel)"\n'
        f'exec "{sys.executable}" "{ROOT}/scripts/cilocal.py" --runner-temp "$(mktemp -d "$SHARED/rt.XXXX")" "$@"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, timeout=60)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, timeout=60)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], cwd=repo, check=True, timeout=60
    )
    return repo, shared


def _ci(repo: Path, shared: Path, *argv: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cilocal.py"), "--runner-temp", str(shared / "rt"), *argv],
        cwd=repo,
        env={
            **os.environ,
            "CI_LOCAL_JOBS": "",
            "CI_LOCAL_WORKERS": "2",
            "SHARED": str(shared),
            "HEADRON_SLOT_LOAD": "1000",
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


class _Fake:
    """A started node on an injected clock: it answers `answer` once the clock reaches `at`."""

    def __init__(self, now: list[float], at: float, answer: MicroResult, live: list[str]) -> None:
        self.now, self.at, self.answer, self.live, self.stopped = now, at, answer, live, False
        live.append(answer.program)

    def poll(self) -> MicroResult | None:
        if self.now[0] < self.at:
            return None
        self.live.remove(self.answer.program)
        return self.answer

    def stop(self) -> None:
        self.stopped = True


def _answer(name: str, status: str = "ok") -> MicroResult:
    return MicroResult(name, "1", status, next=None if status == "ok" else "fix it")


def _graph(nodes: list[Node], at: dict[str, float], status: dict[str, str] | None = None, **kwargs: object):
    """Run `nodes` on a fake clock; returns (results, handles, the most nodes ever live at once)."""
    now, live, handles, peak = [0.0], [], {}, [0]

    def start(node: Node, timeout_s: float) -> _Fake:
        handles[node.name] = _Fake(
            now, now[0] + at[node.name], _answer(node.name, (status or {}).get(node.name, "ok")), live
        )
        peak[0] = max(peak[0], len(live))
        return handles[node.name]

    def wait(seconds: float) -> None:
        now[0] += seconds

    results = micrograph.run(
        nodes,
        start,
        clock=lambda: now[0],
        wait=wait,
        poll_s=1.0,
        **{"budget_s": 1000.0, **kwargs},  # type: ignore[arg-type]
    )
    return results, handles, peak[0]


def graph_cases(module: ModuleType) -> None:
    """micrograph alone, on an injected clock: every way a node that did not finish must not read as ok."""
    _case(
        module,
        "a cycle is named, so a graph that can never finish is refused before anything starts",
        "a scheduler that spins forever on two nodes each waiting for the other",
        any(p.startswith("cycle:") for p in micrograph.problems([Node("a", ("b",), 1), Node("b", ("a",), 1)])),
    )
    results, handles, _ = _graph([Node("a", (), 10), Node("b", ("a",), 10)], {"a": 0, "b": 0}, {"a": "refused"})
    _case(
        module,
        "a node whose need did not answer ok answers unknown, blocked by that need, and never starts",
        "edge coverage paid for, or passed, after a mutation shard failed",
        results["b"].status == "unknown" and "blocked by a" in results["b"].evidence_refs[0] and "b" not in handles,
    )
    results, handles, _ = _graph([Node("a", (), 10)], {"a": 50})
    _case(
        module,
        "a node past its own timeout is stopped and answers unknown, never ok",
        "a hung suite read as a pass because it never exited non-zero",
        results["a"].status == "unknown" and "timed out" in results["a"].evidence_refs[0] and handles["a"].stopped,
    )
    results, handles, _ = _graph([Node("a", (), 100), Node("b", ("a",), 100)], {"a": 50, "b": 0}, budget_s=30.0)
    _case(
        module,
        "once the total budget is spent, the running node is stopped and the waiting one answers unknown",
        "a run that outlives its budget, or a node never started read as ok",
        [results[n].status for n in "ab"] == ["unknown", "unknown"]
        and handles["a"].stopped
        and "not started" in results["b"].evidence_refs[0],
    )
    together = _graph([Node("a", (), 10), Node("b", (), 10)], {"a": 5, "b": 5}, width=2)
    alone = _graph([Node("a", (), 10), Node("b", (), 10)], {"a": 5, "b": 5}, width=2, admit=lambda: False)
    _case(
        module,
        "width caps how many run at once, and past the first a start needs admit(): a loaded machine runs one",
        "three suites started on a machine with no spare cores",
        together[2] == 2 and alone[2] == 1 and all(r.actionable for r in alone[0].values()),
    )
    contract = cipipeline.nodes(cipipeline.selected([]))
    shards = [n.name for n in contract if n.name.startswith("mutation:")]
    blocked = []
    for shard in shards:
        results, _, _ = _graph(contract, {n.name: 0 for n in contract}, {shard: "refused"}, width=3)
        blocked.append(results["edge-coverage"].status == "unknown")
    _case(
        module,
        "in the real declaration, any one mutation shard that is not ok blocks edge-coverage",
        "edge coverage judged over two shards' ledgers because only the first shard was a need",
        len(shards) == 3 and all(blocked),
    )
    _case(
        module,
        "a refusal outranks the unknowns it blocked: the exit is 1; undecided alone is 2; all ok is 0",
        "a run whose fast job failed reported as merely undecided, or an unknown reported as a pass",
        cilocal.verdict([_answer("a", "refused"), _answer("b", "unknown")]) == 1
        and cilocal.verdict([_answer("a"), _answer("b", "unknown")]) == 2
        and cilocal.verdict([_answer("a")]) == 0,
    )


def declaration_cases(module: ModuleType) -> None:
    """cipipeline.problems: the real declaration is clean, and each planted defect is named."""
    step = Step("s", "true", 10)
    cycle = [Job("a", "p", 10, (step,), needs=("b",)), Job("b", "p", 10, (step,), needs=("a",))]
    _case(
        module,
        "the real declaration is a DAG of bounded steps, and a planted cycle is refused",
        "a declaration edit that can never finish, found only when a land hangs",
        cipipeline.problems() == [] and any("cycle" in p for p in cipipeline.problems(cycle)),
    )
    found = cipipeline.problems(
        [
            Job("a", "p", 10, (Step("s", "true", 20),), needs=("ghost",)),
            Job("b", "p", 10, (Step("s", "x", 5, env={"SHARD": "${HEADRON_CI_SHARD}"}),)),
            Job("c", "p", 10, ()),
        ]
    )
    _case(
        module,
        "an undeclared need, a step longer than its job, an empty job and a $ in an env value are each refused",
        "env SHARD='${HEADRON_CI_SHARD}' reaching the step as those characters, so every shard ran the whole suite",
        any("undeclared job 'ghost'" in p for p in found)
        and any("timeout_s 20" in p for p in found)
        and any("c has no steps" in p for p in found)
        and any("holds a $" in p for p in found),
    )


def drift_cases(module: ModuleType) -> None:
    """cidrift reads the native steps: a script only a native step runs must still be a gate or named CI-only."""
    native = [step.run for job in cipipeline.JOBS for step in job.steps]
    undeclared, stale = cidrift.drift(["python scripts/zz_unnamed.py", *native], [], {"scripts/zz_gone.py": "x"})
    _case(
        module,
        "a script a native step runs that no gate names is undeclared, and a CI-only entry no step runs is stale",
        "a script added to cipipeline.py that runs only in CI, judged locally by nothing",
        "scripts/zz_unnamed.py" in undeclared
        and stale == ["scripts/zz_gone.py"]
        and set(cidrift.drift(cidrift.run_texts(), [], {})[0]) >= {"scripts/agentrun.py", "scripts/bench.py"},
    )


def run_cases(module: ModuleType, base: Path) -> None:
    """The real runner over a planted declaration, through its CLI."""
    repo, shared = _repo(base, "plan")
    plan = _ci(repo, shared, "--plan")
    picked = _ci(repo, shared, "--plan", CI_LOCAL_JOBS="join")
    _case(
        module,
        "with no job named, the plan is every unit of the CONTRACT jobs, each after its needs",
        "a hand-kept job list that drops a unit the local-ci status waits on",
        plan.returncode == 0 and plan.stdout.split() == ["first", "pair:a", "pair:b", "join"],
    )
    _case(
        module,
        "CI_LOCAL_JOBS picks exactly those jobs, as ~/.claude/bin/ci-local -j exports it",
        "a named job that silently pays for every job it needs first",
        picked.returncode == 0 and picked.stdout.split() == ["join"],
    )
    repo, shared = _repo(base, "whole")
    with_env = {"CI_LOCAL_WORKERS": "2"}
    whole = _ci(repo, shared, **with_env)
    lines = whole.stdout.splitlines()
    trees = subprocess.run(
        ["git", "worktree", "list"], cwd=repo, capture_output=True, text=True, check=True, timeout=60
    )
    _case(
        module,
        "a clean whole run starts ready shards together, each in its own tree, joined through one artifact store",
        "two shards chained, or planting defects into one tree, or a union that never sees a shard's ledger",
        whole.returncode == 0 and (shared / "union").read_text(encoding="utf-8").split() == ["a", "b"],
    )
    _case(
        module,
        "one unit's output prints whole, so shards running together never interleave",
        "a log nobody can read because two shards share one stream",
        "start a" in lines
        and lines.index("end a") - lines.index("start a") == 1
        and lines.index("end b") - lines.index("start b") == 1,
    )
    _case(
        module,
        "every unit's worktree is gone when the run ends",
        "a worktree per shard left behind by every land",
        len(trees.stdout.splitlines()) == 1,
    )
    repo, shared = _repo(base, "broken")
    broken = _ci(repo, shared, PLANT="first")
    _case(
        module,
        "a refused unit makes the run exit 1 and blocks what needs it, transitively",
        "a mutation suite paid for after fast failed, or a green because the failed child's exit was dropped",
        broken.returncode == 1
        and "blocked by first" in broken.stdout
        and "blocked by pair:a" in broken.stdout
        and not (shared / "a").exists(),
    )
    repo, shared = _repo(base, "killed")
    killed = _ci(repo, shared, PLANT="kill")
    _case(
        module,
        "a child killed by a signal is unknown, never ok: the run exits 2 and blocks what needs it",
        "a negative or 137 exit mapped to a pass because only 1 was read as failure",
        killed.returncode == 2 and "child exit -9" in killed.stdout and "blocked by first" in killed.stdout,
    )
    repo, shared = _repo(base, "dirty", ALONE)
    (repo / "dirty.txt").write_text("edited\n", encoding="utf-8")
    dirty = _ci(repo, shared)
    _case(
        module,
        "a dirty tree runs in place, one unit at a time, so its edits are what gets judged",
        "a green for HEAD reported on a tree whose edits never ran",
        dirty.returncode == 0 and "edited" in (shared / "dirty").read_text(encoding="utf-8"),
    )
    repo, shared = _repo(base, "serial", ALONE)
    serial = _ci(repo, shared, CI_LOCAL_WORKERS="1")
    _case(
        module,
        "width 1 runs in place through the same steps",
        "no way to take the fan-out away when it is the suspect",
        serial.returncode == 0 and "::: started" not in serial.stdout,
    )
    repo, shared = _repo(base, "loaded", ALONE)
    loaded = _ci(repo, shared, HEADRON_SLOT_LOAD="0")
    _case(
        module,
        "on a machine with no spare cores, units run one at a time and still pass",
        "three suites on a loaded machine: the starved desktop and timed-out suites slot.py measured",
        loaded.returncode == 0 and "::: started pair" in loaded.stdout,
    )
    repo, shared = _repo(base, "unit", ALONE)
    one = _ci(repo, shared, "--unit", "pair:a")
    nothing = _ci(repo, shared, "--unit", "pair:z")
    _case(
        module,
        "--unit runs that one unit alone, and a unit nothing declares is refused, never an empty pass",
        "both shards in every shard's child, or a typo'd unit passing by running nothing",
        one.returncode == 0 and "start a" in one.stdout and "start b" not in one.stdout and nothing.returncode == 1,
    )
    slow, toolless, hosted = (_ci(repo, shared, job) for job in ("slow", "toolless", "hosted"))
    _case(
        module,
        "a hung step, a missing tool and a hosted-only step each answer unknown (exit 2), and the last two never run",
        "a timeout or a skipped step reported as a pass",
        (slow.returncode, toolless.returncode, hosted.returncode) == (2, 2, 2)
        and "timed out after 1s" in slow.stdout
        and "no-such-tool-zq not on PATH" in toolless.stdout
        and "OIDC token" in hosted.stdout
        and not (shared / "ran").exists(),
    )
    outside = base / "outside"
    outside.mkdir()
    bare = subprocess.run(["git", "init", "-q", str(base / "bare")], check=True, timeout=60)
    _case(
        module,
        "`headron ci` runs the checkout's own CI, and refuses outside a checkout or in one that declares none",
        "an installed headron judging a lane by main's jobs, or a blind run that exits 0",
        isinstance(ci.shim(repo), Path)
        and "not inside a git checkout" in str(ci.shim(outside))
        and "declares no native CI" in str(ci.shim(base / "bare"))
        and bare.returncode == 0,
    )


def hook_cases(module: ModuleType, base: Path) -> None:
    """The opt-in hook through the real command, in a real repository: it writes and removes only its own."""
    repo = base / "hook"
    repo.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"GIT_CONFIG_GLOBAL": os.devnull}
    hook = repo / ".git" / "hooks" / "pre-push"

    def run(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, cwd=repo, capture_output=True, text=True, check=False, env=env, timeout=60)

    def tool(flag: str) -> int:
        return run(sys.executable, str(Path(cilocal.__file__)), flag).returncode

    run("git", "init", "-q")
    hook.unlink(missing_ok=True)
    installed = tool("--install-hook")
    body, hook_mode = hook.read_text("utf-8"), hook.stat().st_mode
    again = tool("--install-hook")
    removed = tool("--uninstall-hook")
    gone = not hook.exists()
    repeat = tool("--uninstall-hook")
    _case(
        module,
        "--install-hook writes an executable hook that runs `fast`; reinstalling holds; --uninstall-hook removes it",
        "a hook that never runs the fast job, or an uninstall that leaves it",
        cilocal.HOOK_MARK in body
        and '/.github/ci-local.sh" fast' in body
        and hook_mode & 0o111 == 0o111
        and not (installed or again or removed or repeat)
        and gone,
    )
    foreign = "#!/bin/sh\necho someone else\n"
    hook.write_text(foreign, "utf-8")
    refused = (tool("--install-hook"), tool("--uninstall-hook"))
    _case(
        module,
        "a pre-push hook this did not write is refused both ways and left as it was",
        "someone else's hook overwritten or deleted",
        refused == (1, 1) and hook.read_text("utf-8") == foreign,
    )
    hook.unlink()
    run("git", "config", "core.hooksPath", "tracked-hooks")
    shared = tool("--install-hook")
    _case(
        module,
        "a set core.hooksPath is this repository's code: refused, with nothing written",
        "a hook written into tracked code, or beside a directory git ignores it for",
        shared == 1 and not hook.exists() and not (repo / "tracked-hooks").exists(),
    )


def rescue_tag_cases(module: ModuleType, base: Path) -> None:
    """Real tags in a real repository: every retry's tag goes on a merge, and only there."""
    repo = base / "rescue"
    repo.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False, env=env, timeout=60
        )
        return done.stdout.strip() if done.returncode == 0 else ""

    identity = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")
    git("init", "-q")
    git(*identity, "commit", "-q", "--allow-empty", "-m", "first")
    first = cilocal.tag_rescue("fix/lane", git)
    git(*identity, "commit", "-q", "--allow-empty", "-m", "rebased")
    second = cilocal.tag_rescue("fix/lane", git)
    git("tag", "lane/fix-lane-2/sibling")
    git("tag", "v1.0.0")
    tags = {first, second, "lane/fix-lane-2/sibling", "v1.0.0"}
    _case(
        module,
        "a retry after a rebase tags its own tip beside the one before it",
        "a rescue tag named for the branch alone, moved off the commit a refused retry still needs",
        first != second and set(git("tag", "--list").split()) == tags,
    )
    held = [cilocal.close_landing("fix/lane", verdict, git) for verdict in ("armed: auto-merge set", "queued", "open")]
    _case(
        module,
        "a landing that has not merged keeps every rescue tag, and exits by its verdict",
        "a rescue tag dropped while the commit may still need it",
        held == [0, 0, 1] and set(git("tag", "--list").split()) == tags,
    )
    _case(
        module,
        "a merged landing drops that lane's rescue tags and no other tag",
        "rescue tags left standing after the merge, each reading as work still to review",
        cilocal.close_landing("fix/lane", "merged", git) == 0
        and set(git("tag", "--list").split()) == {"lane/fix-lane-2/sibling", "v1.0.0"},
    )


def run(module: ModuleType) -> None:
    with tempfile.TemporaryDirectory(prefix="headron-cilocal-") as directory:
        base = Path(directory)
        graph_cases(module)
        declaration_cases(module)
        drift_cases(module)
        run_cases(module, base)
        rescue_tag_cases(module, base)
        hook_cases(module, base)
