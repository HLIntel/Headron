#!/usr/bin/env python3
"""Planted workflows through cilocal's public CLI: each translator is observed by what a real step saw."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import cilocal
from seats_test import _case

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW = """
jobs:
  up:
    strategy:
      matrix:
        k: [a, b]
    env:
      JOB: job-${{ matrix.k }}
    steps:
      - name: see the matrix
        env:
          K: ${{ matrix.k }}
        run: echo "$JOB $K ${{ matrix.k }}" >> "$RUNNER_TEMP/seen" && echo "$K" > "${{ runner.temp }}/edge-$K.txt"
      - name: share it
        uses: actions/upload-artifact@v9
        with:
          name: edge-${{ matrix.k }}
          path: ${{ runner.temp }}/edge-${{ matrix.k }}.txt
          if-no-files-found: error
  down:
    needs: [up]
    steps:
      - uses: actions/download-artifact@v9
        with:
          pattern: edge-*
          path: ${{ runner.temp }}/joined
          merge-multiple: true
      - name: join
        run: cat "$RUNNER_TEMP/joined/edge-a.txt" "$RUNNER_TEMP/joined/edge-b.txt" > "$RUNNER_TEMP/union"
  incomplete:
    steps:
      - name: unknown
        run: echo "${{ github.sha }}"
  action:
    steps:
      - uses: example/unknown@v1
  setup_valid:
    steps:
      - uses: actions/checkout@v9
      - uses: actions/setup-python@v9
        with:
          python-version: "PYTHON_VERSION"
  setup:
    steps:
      - uses: actions/setup-python@v9
        with:
          python-version: "99.1"
      - uses: astral-sh/setup-uv@v9
      - uses: actions/checkout@v9
        with:
          ref: other-branch
      - uses: actions/checkout@v9
        if: github.event_name == 'push'
        with:
          ref: other-branch
  gates:
    steps:
      - name: unknown
        run: echo "${{ github.sha }}" > "$RUNNER_TEMP/unknown"
      - name: odd condition
        if: github.event_name == 'push'
        run: touch "$RUNNER_TEMP/odd"
      - name: root install
        run: |
          curl --version > /dev/null
          sudo install -m 0755 gitleaks /usr/local/bin/gitleaks
      - name: breaks
        run: exit 3
      - name: after a failure
        run: touch "$RUNNER_TEMP/after"
      - name: cleanup
        if: ${{ always() }}
        run: touch "$RUNNER_TEMP/always"
  contract:
    needs: [down]
    steps:
      - run: "true"
"""


FANOUT = """
jobs:
  first:
    steps:
      - name: see the tree
        run: |
          cat dirty.txt >> "$SHARED/dirty" || true
          [ "$PLANT" != first ] || exit 3
  pair:
    needs: [first]
    strategy:
      matrix:
        k: [a, b]
    steps:
      - name: meet the other row
        run: |
          echo "start ${{ matrix.k }}"
          touch "mine-${{ matrix.k }}" "$SHARED/${{ matrix.k }}"
          MEET
          [ "$(ls mine-*)" = "mine-${{ matrix.k }}" ] || exit 8
          rm "mine-${{ matrix.k }}"
          echo "${{ matrix.k }}" > "$RUNNER_TEMP/edge-${{ matrix.k }}.txt"
          echo "end ${{ matrix.k }}"
      - name: share it
        uses: actions/upload-artifact@v9
        with:
          name: edge-${{ matrix.k }}
          path: ${{ runner.temp }}/edge-${{ matrix.k }}.txt
          if-no-files-found: error
  join:
    needs: [pair]
    steps:
      - uses: actions/download-artifact@v9
        with:
          pattern: edge-*
          path: ${{ runner.temp }}/joined
          merge-multiple: true
      - name: join
        run: cat "$RUNNER_TEMP/joined/edge-a.txt" "$RUNNER_TEMP/joined/edge-b.txt" > "$SHARED/union"
  contract:
    needs: [join]
    steps:
      - run: "true"
"""
TOGETHER = """for _ in $(seq 100); do [ -e "$SHARED/a" ] && [ -e "$SHARED/b" ] && break; sleep 0.1; done; [ -e "$SHARED/a" ] && [ -e "$SHARED/b" ] || exit 9"""  # noqa: E501
ALONE = 'mkdir "$SHARED/busy" || exit 7; sleep 0.5; rmdir "$SHARED/busy"'


def _replay_repo(base: Path, name: str, workflow: str, meet: str = TOGETHER) -> tuple[Path, Path]:
    """A committed repository whose ci-local.sh is the real replay, as a fan-out child runs it."""
    repo, shared = base / name, base / f"{name}-shared"
    (repo / ".github").mkdir(parents=True)
    shared.mkdir()
    (repo / "ci.yml").write_text(workflow.replace("MEET", meet), encoding="utf-8")
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


def _replay(repo: Path, shared: Path, *argv: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "cilocal.py"),
            "--workflow",
            "ci.yml",
            "--runner-temp",
            str(shared / "rt"),
        ]
        + list(argv),
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
        timeout=60,
    )


def fan_out_cases(module: ModuleType, base: Path) -> None:
    completed = SimpleNamespace(poll=lambda: 0)
    with (
        patch.object(cilocal, "_start_unit", return_value=completed),
        patch.object(cilocal, "_finish_unit"),
        patch.object(cilocal, "wait_until") as wait,
    ):
        result = cilocal.fan_out("ci.yml", {"first": [], "next": ["first"]}, "head", base / "instant", 2)
    _case(
        module,
        "completed units immediately release their dependents without an empty wait",
        "a scheduler that waits for a child after all children have exited",
        result == 0 and not wait.called,
    )
    repo, shared = _replay_repo(base, "whole", FANOUT)
    with patch.dict(os.environ, {"CI_LOCAL_WORKERS": "1"}):
        whole = _replay(repo, shared)
    lines = whole.stdout.splitlines()
    _case(
        module,
        "a clean whole replay runs ready rows together, each in its own tree, and joins them through one store",
        "two shards chained, or planting defects into one tree, or a union that never sees a shard's ledger",
        whole.returncode == 0 and (shared / "union").read_text(encoding="utf-8").split() == ["a", "b"],
    )
    _case(
        module,
        "one unit's output prints whole, so rows running together never interleave",
        "a log nobody can read because two shards share one stream",
        lines.index("end a") - lines.index("start a") == 1 and lines.index("end b") - lines.index("start b") == 1,
    )
    trees = subprocess.run(
        ["git", "worktree", "list"], cwd=repo, capture_output=True, text=True, check=True, timeout=60
    )
    _case(
        module,
        "every unit's worktree is gone when the replay ends",
        "a worktree per row left behind by every land",
        len(trees.stdout.splitlines()) == 1,
    )
    repo, shared = _replay_repo(base, "broken", FANOUT)
    broken = _replay(repo, shared, PLANT="first")
    _case(
        module,
        "a failed unit fails the replay and SKIPs what needs it, transitively",
        "a mutation suite paid for after fast failed, or a green because the failed child's exit was dropped",
        broken.returncode == 1
        and "SKIP unit pair[k=a]" in broken.stdout
        and "SKIP unit join" in broken.stdout
        and not (shared / "a").exists(),
    )
    repo, shared = _replay_repo(
        base, "open", FANOUT.replace("cat dirty.txt >>", "echo ${{ github.sha }}; cat dirty.txt >>")
    )
    still_open = _replay(repo, shared)
    _case(
        module,
        "an unresolved step in a child leaves the whole replay incomplete and unsuccessful",
        "a SKIP inside a fanned-out unit reported as a green land",
        still_open.returncode == 1 and "${{ github.sha }}" in still_open.stdout and "1 skipped" in still_open.stdout,
    )
    repo, shared = _replay_repo(base, "absent", FANOUT.replace("pattern: edge-*", "pattern: absent-*"))
    absent = _replay(repo, shared)
    _case(
        module,
        "a download with no matching artifact fails the replay",
        "edge coverage judged over no ledger, and passed",
        absent.returncode == 1 and "no artifact matches absent-*" in absent.stdout,
    )
    repo, shared = _replay_repo(base, "dirty", FANOUT, ALONE)
    (repo / "dirty.txt").write_text("edited\n", encoding="utf-8")
    dirty = _replay(repo, shared)
    _case(
        module,
        "a dirty tree replays in place, one at a time, so its edits are what gets judged",
        "a green for HEAD reported on a tree whose edits never ran",
        dirty.returncode == 0 and "edited" in (shared / "dirty").read_text(encoding="utf-8"),
    )
    repo, shared = _replay_repo(base, "serial", FANOUT, ALONE)
    serial = _replay(repo, shared, CI_LOCAL_WORKERS="1")
    _case(
        module,
        "width 1 replays in place through the same steps",
        "no way to take the fan-out away when it is the suspect",
        serial.returncode == 0 and "::: started" not in serial.stdout,
    )
    repo, shared = _replay_repo(base, "loaded", FANOUT, ALONE)
    loaded = _replay(repo, shared, HEADRON_SLOT_LOAD="0")
    _case(
        module,
        "on a machine with no spare cores, units run one at a time and still pass",
        "three suites on a loaded machine: the starved desktop and timed-out suites slot.py measured",
        loaded.returncode == 0 and "::: started pair" in loaded.stdout,
    )
    repo, shared = _replay_repo(base, "picked", FANOUT, ALONE)
    picked = _replay(repo, shared, "pair[k=a]")
    unknown = _replay(repo, shared, "pair[k=z]")
    _case(
        module,
        "a named row runs only that row, and a row nothing declares is incomplete, never an empty pass",
        "both shards in every shard's unit, or a typo'd unit passing by running nothing",
        picked.returncode == 0
        and "start a" in picked.stdout
        and "start b" not in picked.stdout
        and unknown.returncode == 1,
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
        workflow = base / "ci.yml"
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        workflow.write_text(textwrap.dedent(WORKFLOW).replace("PYTHON_VERSION", version), encoding="utf-8")
        # THE HOST'S `python` IS NOT ASSUMED: the adapter asks `python --version`, and a host with only
        # python3 on PATH answered "unavailable" where the case expects a version mismatch. The version
        # above is this interpreter's, so `python` is made to be this interpreter.
        shim = base / "bin"
        shim.mkdir()
        (shim / "python").symlink_to(sys.executable)
        path = os.pathsep.join((str(shim), os.environ.get("PATH", "")))

        def call(*argv: str, env: dict[str, str] | None = None, temp: str = "rt") -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "cilocal.py"),
                    "--workflow",
                    str(workflow),
                    "--runner-temp",
                    str(base / temp),
                    *argv,
                ],
                cwd=base,
                env={**os.environ, "PATH": path, **(env or {})},
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

        plan = call("--plan", env={"CI_LOCAL_JOBS": ""})
        _case(
            module,
            "with no job named, the plan is the contract job's needs, each after its own",
            "a hand-kept job list that drops a job the required check waits on",
            plan.returncode == 0 and plan.stdout.split() == ["up", "down"],
        )
        picked = call("--plan", env={"CI_LOCAL_JOBS": "down"})
        _case(
            module,
            "CI_LOCAL_JOBS picks the jobs, as ~/.claude/bin/ci-local -j exports it",
            "a -j subset that silently runs the full default set",
            picked.stdout.split() == ["down"],
        )

        joined = call("up", "down")
        rt = base / "rt"
        seen = (rt / "seen").read_text(encoding="utf-8").split("\n") if (rt / "seen").exists() else []
        _case(
            module,
            "a matrix runs once per value with job env, step env and the run text all translated",
            "env: blocks ignored, or a raw ${{ matrix }} handed to bash as a bad substitution",
            joined.returncode == 0 and seen[:2] == ["job-a a a", "job-b b b"],
        )
        _case(
            module,
            "an upload and a download join the shards through RUNNER_TEMP",
            "edge-coverage never replayed, so a local green is not the required check's green",
            (rt / "union").read_text(encoding="utf-8") == "a\nb\n" if (rt / "union").exists() else False,
        )
        setup = call("setup", temp="setup")
        valid = call("setup_valid", temp="setup-valid")
        with patch.object(cilocal.shutil, "which", return_value=None):
            unpinned_without_tools = cilocal._setup("astral-sh/setup-uv", {})
        _case(
            module,
            "untranslated setup and its condition cannot produce a successful replay",
            "a setup action silently passed over despite a mismatched version or unsupported condition",
            setup.returncode != 0
            and "host tool version does not match 99.1" in setup.stdout
            and "tool version is unpinned" in setup.stdout
            and unpinned_without_tools == "tool version is unpinned or unavailable"
            and "checkout options are not translated" in setup.stdout
            and "the condition" in setup.stdout,
        )
        _case(
            module,
            "default checkout and matching Python use narrow local adapters",
            "valid local setup rejected or silently passed without checking the version",
            valid.returncode == 0 and valid.stdout.count("local setup adapter") == 2,
        )

        incomplete = call("incomplete", temp="incomplete")
        _case(
            module,
            "an unresolved required step cannot produce a successful replay",
            "a skipped required step reported as a green local check",
            incomplete.returncode != 0 and "SKIP incomplete: unknown" in incomplete.stdout,
        )

        unknown_action = call("action", temp="action")
        _case(
            module,
            "an unknown action cannot produce a successful replay",
            "an unimplemented action silently treated as toolchain setup",
            unknown_action.returncode != 0 and "action is not translated" in unknown_action.stdout,
        )

        gates = call("gates", temp="gt")
        gt = base / "gt"
        _case(
            module,
            "an expression nothing answers is SKIP with its text, never PASS and never run",
            "a step run with ${{ github.sha }} left raw",
            "SKIP gates: unknown — unresolved ${{ github.sha }}" in gates.stdout and not (gt / "unknown").exists(),
        )
        _case(
            module,
            "an untranslated if: is SKIP with the condition, not run",
            "a condition dropped, so a push-only step runs on every replay",
            "the condition \"github.event_name == 'push'\" is not translated" in gates.stdout
            and not (gt / "odd").exists(),
        )
        _case(
            module,
            "a step that needs sudo is SKIP: root installs are runner-only, never a password prompt FAIL",
            "the pinned scanner install failing locally on sudo and cascading success() skips over the job",
            "SKIP gates: root install — needs sudo" in gates.stdout,
        )
        _case(
            module,
            "after a failure, success() steps are skipped, always() steps run, and the exit is 1",
            "every step replayed after a failure as if if: did not exist",
            gates.returncode == 1
            and not (gt / "after").exists()
            and (gt / "always").exists()
            and "ci-local.sh: 1 failed" in gates.stdout,
        )
        fan_out_cases(module, base)
        rescue_tag_cases(module, base)
        hook_cases(module, base)
