"""Landing and lifecycle regression groups, split from the general guard suite."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import safeedit

T: Any = None


def run(module: ModuleType):
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
    merge_method_cases()
    fast_gate_cases()
    full_replay_cases()
    shard_split_cases()
    repo_reach_cases()
    local_ci_cases()
    immediate_merge_cases()
    consumer_gate_cases()
    consumer_placement_cases()
    consumer_check_cases()
    gate_adoption_cases()
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


def merge_method_cases() -> None:
    """A lane carrying a merge commit squashes; a linear-history base refuses its rebase merge."""
    import branchstate

    real = branchstate._git
    try:
        for merges, want in (("1", "--squash"), ("0", "--rebase"), ("", "--rebase")):
            branchstate._git = lambda *a, m=merges: m if a[:3] == ("rev-list", "--count", "--merges") else ""
            got = branchstate.merge_method("origin/main", "lane")
            if got != want:
                raise SystemExit(f"FAIL a lane with merges={merges!r} armed {got}, expected {want}")
    finally:
        branchstate._git = real
    CASES.append(
        (
            "a lane carrying a merge commit is squash-merged, every other lane rebase-merged",
            "a rebase merge armed on a linear-history base, refused and escalated as two writers",
        )
    )
    print("  ok    a lane carrying a merge commit is squash-merged, every other lane rebase-merged")


def fast_gate_cases() -> None:
    """The pre-push hook's gate runs as a landing step: red is the commit (65), and nothing is pushed."""
    import types

    import branchstate

    calls: list[list[str]] = []
    noise = "\x1b[90m12:41PM\x1b[0m \x1b[32mINF\x1b[0m scanned ~16 MB"

    def fake(argv: Sequence[str], **_):
        calls.append(list(argv))
        code = 1 if argv[-1] == "fast" or argv[:2] == ["git", "show-ref"] else 0
        return subprocess.CompletedProcess(argv, code, f"{noise}\n" * 40 + "pyright: 4 errors", "")

    names = ("subprocess", "_git", "_tree", "_is_atlas", "clean_checkout_errors", "_pull_request")
    real = {n: getattr(branchstate, n) for n in names}
    with tempfile.TemporaryDirectory() as tree:
        (Path(tree) / ".github").mkdir()
        (Path(tree) / ".github" / "ci-local.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        fakes = {
            "subprocess": types.SimpleNamespace(run=fake, TimeoutExpired=subprocess.TimeoutExpired),
            "_git": lambda *a: "1" if a[:2] == ("rev-list", "--count") and "--merges" not in a else "",
            "_tree": lambda: Path(tree),
            "_is_atlas": lambda: False,
            "clean_checkout_errors": lambda *a: None,
            "_pull_request": lambda b: (None, True),
        }
        for name, value in fakes.items():
            setattr(branchstate, name, value)
        try:
            code = branchstate._land_once("lane")
        finally:
            for name, value in real.items():
                setattr(branchstate, name, value)
    if code != 65 or any(c[:2] == ["git", "push"] for c in calls):
        raise SystemExit(
            f"FAIL a red fast gate returned {code} and pushed={any(c[:2] == ['git', 'push'] for c in calls)}"
        )
    CASES.append(
        (
            "a red pre-push fast gate refuses the landing as the commit (65) before any push",
            "a type error the hook refused, retried and escalated as two writers behind gitleaks INF lines",
        )
    )
    print("  ok    a red pre-push fast gate refuses the landing as the commit (65) before any push")


def full_replay_cases() -> None:
    """The atlas's full replay runs before the push: red publishes nothing, green is not run twice."""
    import types

    import branchstate

    events: list[str] = []
    verdict = False

    def fake(argv: Sequence[str], **_):
        events.append(" ".join(argv[:2]))
        return subprocess.CompletedProcess(argv, 1 if argv[:2] == ["git", "show-ref"] else 0, "", "")

    def replay(_tree: Path, sha: str) -> bool:
        events.append(f"replay {sha}")
        return verdict

    def post(_branch: str, _tree: Path, _git: object, replayed: str = "") -> bool:
        events.append(f"post {replayed}")
        return True

    fakes = {
        "subprocess": types.SimpleNamespace(run=fake, TimeoutExpired=subprocess.TimeoutExpired),
        "_git": lambda *a: "1" if a[:2] == ("rev-list", "--count") else "abc" if a[0] == "rev-parse" else "",
        "_is_atlas": lambda: True,
        "clean_checkout_errors": lambda *a: None,
        "_pull_request": lambda b: (None, True),
        "replay_local_ci": replay,
        "post_local_ci": post,
    }
    real = {name: getattr(branchstate, name) for name in fakes}
    for name, value in fakes.items():
        setattr(branchstate, name, value)
    try:
        code = branchstate._land_once("lane")
        red = list(events)
        events.clear()
        verdict = True
        branchstate._land_once("lane")
    finally:
        for name, value in real.items():
            setattr(branchstate, name, value)
    if code != 65 or "git push" in red or "replay abc" not in red:
        raise SystemExit(f"FAIL a red full replay must refuse before any push: {code} {red}")
    if not events.index("replay abc") < events.index("git push") < events.index("post abc") or any(
        "ci-local.sh" in event for event in events
    ):
        raise SystemExit(f"FAIL a green replay must precede the push and post without a second gate: {events}")

    import cilocal

    replays: list[str] = []
    states: list[str] = []

    def gh(argv: Sequence[str], **_):
        states.append(argv[6])
        return subprocess.CompletedProcess(argv, 0, "", "")

    def posted(replayed: str, green: bool) -> tuple[bool, list[str], list[str]]:
        replays.clear()
        states.clear()
        cilocal.replay_local_ci = lambda _tree, sha: bool(replays.append(sha)) or green
        return cilocal.post_local_ci("lane", Path("."), lambda *_: "abc", replayed), list(replays), list(states)

    real_replay, real_subprocess = cilocal.replay_local_ci, cilocal.subprocess
    cilocal.subprocess = types.SimpleNamespace(run=gh)
    try:
        reused, other, refused = posted("abc", False), posted("old", True), posted("old", False)
    finally:
        cilocal.replay_local_ci, cilocal.subprocess = real_replay, real_subprocess
    success = ["state=pending", "state=success"]
    if reused != (True, [], success) or other != (True, ["abc"], success) or refused != (False, ["abc"], success[:1]):
        raise SystemExit(f"FAIL only a replay of this exact commit stands for it: {reused} {other} {refused}")
    CASES.append(
        (
            "the atlas's full replay runs before the push and a red one publishes nothing",
            "a red shard after the push stranded a published lane that may only merge, never rebase",
        )
    )
    print("  ok    the atlas's full replay runs before the push and a red one publishes nothing")


def shard_split_cases() -> None:
    """A whole-suite run refuses a total that moved without its guards pin, before any shard job runs."""
    import types

    import testgroups

    pinned = testgroups.GUARDS_CASES
    if testgroups.split_moved(pinned) or testgroups.split_moved(None) or not testgroups.split_moved(pinned + 1):
        raise SystemExit("FAIL split_moved must name a moved split and nothing else")
    suite = types.ModuleType("suite")
    vars(suite).update(CASES=[0, 0])
    real = testgroups.impact
    testgroups.impact = types.SimpleNamespace(save=lambda: None)
    try:
        testgroups.finish_suite(suite, 2, pinned + 1)
    except SystemExit as exc:
        said = str(exc)
    else:
        said = ""
    finally:
        testgroups.impact = real
    if "SHARD SPLIT MOVED" not in said:
        raise SystemExit(f"FAIL finish_suite passed a moved split: {said!r}")
    CASES.append(
        (
            "a whole-suite run refuses a split the guards pin disagrees with",
            "a lane moved the total alone, passed verify, and failed its shard only after the push",
        )
    )
    print("  ok    a whole-suite run refuses a split the guards pin disagrees with")


def repo_reach_cases() -> None:
    """A fixture's git cannot reach this repository's settings, and a group that does is named."""
    import types

    import testgroups

    decoy = {"GIT_DIR": "/nonexistent/decoy", "GIT_INDEX_FILE": "/nonexistent/index", "GIT_COMMON_DIR": "/nonexistent"}
    saved = {name: os.environ.get(name) for name in decoy}
    os.environ.update(decoy)
    try:
        testgroups.scrub_git_env()
        left = sorted(name for name in decoy if name in os.environ)
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    if left:
        raise SystemExit(f"FAIL the suite kept git's own variables for its fixtures: {left}")
    CASES.append(
        (
            "the suite drops the git variables a hook exports",
            "a fixture's git init obeyed the pre-push hook's GIT_DIR over -C and set core.bare on the real repository",
        )
    )
    print("  ok    the suite drops the git variables a hook exports")

    real = testgroups.impact
    with tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True, timeout=60)
        left_alone = types.SimpleNamespace(CASES=[])
        reached = types.SimpleNamespace(CASES=[])
        testgroups.impact = types.SimpleNamespace(ROOT=repo, enter=lambda: None, leave=lambda *_: None)
        try:
            testgroups.run_group(left_alone, "quiet", lambda _: None)
            testgroups.run_group(
                reached,
                "stray",
                lambda _: subprocess.run(
                    ["git", "-C", repo, "config", "user.name", "tester"], check=True, capture_output=True, timeout=60
                ),
            )
        finally:
            testgroups.impact = real
    said = " ".join(getattr(reached, "SUITE_ERRORS", []))
    if getattr(left_alone, "SUITE_ERRORS", []) or not said.startswith("stray:") or "REWROTE" not in said:
        raise SystemExit(f"FAIL a group that rewrote the repository's settings was not named: {said!r}")
    CASES.append(
        (
            "a planted group that rewrites the repository's settings is named",
            "a fixture identity landed in the shared config, and only the next git status showed anything was wrong",
        )
    )
    print("  ok    a planted group that rewrites the repository's settings is named")


def local_ci_cases() -> None:
    """A failed replay never publishes a successful required status."""
    import types

    import cilocal

    calls = []
    rc = 0

    def fake(argv: Sequence[str], **kwargs: object):
        calls.append((list(argv), kwargs))
        code = rc if str(argv[0]).endswith("ci-local.sh") else 0
        return subprocess.CompletedProcess(argv, code, "", "")

    names = ("subprocess",)
    real = {name: getattr(cilocal, name) for name in names}
    try:
        cilocal.subprocess = types.SimpleNamespace(run=fake, TimeoutExpired=subprocess.TimeoutExpired)
        for rc, expected in ((0, True), (1, False)):
            calls.clear()
            if cilocal.post_local_ci("lane", Path.cwd(), lambda *args: "abc123") != expected:
                raise SystemExit("FAIL local-ci replay verdict was not respected")
            states = [a for args, _ in calls for a in args if a.startswith("state=")]
            if states != (["state=pending", "state=success"] if expected else ["state=pending"]):
                raise SystemExit(f"FAIL unexpected local-ci statuses: {states}")
            replay = [kwargs for args, kwargs in calls if str(args[0]).endswith("ci-local.sh")]
            if len(replay) != 1 or replay[0]["env"]["CI_LOCAL_JOBS"]:
                raise SystemExit("FAIL local-ci did not request the complete contract")
        rc, runs = 1, []
        for replayed in ("abc123", "other"):
            calls.clear()
            cilocal.post_local_ci("lane", Path.cwd(), lambda *args: "abc123", replayed)
            runs.append(sum(str(args[0]).endswith("ci-local.sh") for args, _ in calls))
        if runs != [0, 1]:
            raise SystemExit(f"FAIL only the exact replayed head skips the replay: {runs}")
    finally:
        for name, value in real.items():
            setattr(cilocal, name, value)
    CASES.append(
        ("landing posts success only after full local-ci replay", "a partial replay passes the required status")
    )
    print("  ok    landing posts success only after full local-ci replay")


def immediate_merge_cases() -> None:
    """An immediately merged PR is accepted only for the exact head and base."""
    import json

    import cilocal

    rows = [{"headRefOid": "abc", "baseRefName": "main"}]
    git = lambda *args: "abc"  # noqa: E731
    gh = lambda *args: subprocess.CompletedProcess(args, 0, json.dumps(rows), "")  # noqa: E731
    if not cilocal.merged_head("lane", "main", git, gh):
        raise SystemExit("FAIL immediate merge of the exact head was not accepted")
    rows[0]["headRefOid"] = "old"
    if cilocal.merged_head("lane", "main", git, gh):
        raise SystemExit("FAIL a stale merged head was accepted")
    rows[0].update(headRefOid="abc", baseRefName="other")
    if cilocal.merged_head("lane", "main", git, gh):
        raise SystemExit("FAIL a merge into another base was accepted")
    CASES.append(("immediate merge matches exact head and base", "a merged PR was retried as stranded"))
    print("  ok    an immediate merge is accepted only for its exact head and base")


def consumer_placement_cases() -> None:
    """A per-project runner runs once, in its project; a crate member is not fed to bare rustc; and a
    manifest above the repository is not this file's project. MEASURED AT 3.62.0 on 8 public repositories:
    29 of 82 FAIL rows were these verbs run from the tree root, against changes that broke nothing."""
    import verify  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as top:
        (Path(top) / "Cargo.toml").write_text("")  # ABOVE .git: a stray parent manifest, not the project
        repo, stubs, log = Path(top) / "repo", Path(top) / "stubs", Path(top) / "ran.log"
        stubs.mkdir()
        for tool in ("cargo", "go", "rustc", "rustfmt"):
            (stubs / tool).write_text(f'#!/bin/sh\necho "$(basename "$0") $* @ $PWD" >> "{log}"\n')
            (stubs / tool).chmod(0o755)
        files = {
            "crate/Cargo.toml": "",
            "crate/src/lib.rs": "",
            "crate/src/io.rs": "",
            "mod/go.mod": "",
            "mod/pkg/a.go": "package pkg\n",
            "loose/x.rs": "fn main() {}\n",
        }
        subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=60)
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], check=True, timeout=60)
        for rel, body in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(body)
        subprocess.run([*git, "add", "-A"], check=True, timeout=60)  # staged: the change a consumer's verify reads
        saved = os.environ["PATH"]
        os.environ["PATH"] = f"{stubs}{os.pathsep}{saved}"
        try:
            rows = verify.consumer_rows(repo.resolve(), base="HEAD")
        finally:
            os.environ["PATH"] = saved
        ran = log.read_text().splitlines() if log.exists() else []
        home = str(repo.resolve())
        want = [
            f"cargo test @ {home}/crate",
            f"go test ./... @ {home}/mod",
            f"go vet ./... @ {home}/mod",
            f"rustc loose/x.rs @ {home}",
        ]
        missing = [w for w in want if ran.count(w) != 1]
        if missing:
            raise SystemExit(f"FAIL a per-project runner did not run once in its project: {missing} in {ran}")
        if any(line.startswith("rustc crate/") or line.endswith(f"@ {home}") and "cargo" in line for line in ran):
            raise SystemExit(f"FAIL a crate member went to bare rustc, or a parent manifest was taken: {ran}")
        unplaced = [r for r in rows if r.get("id") == "unit_tests:loose/x.rs" and r.get("verdict") == "NOT RUN"]
        if not unplaced or "Cargo.toml" not in str(unplaced[0].get("why")):
            raise SystemExit(f"FAIL a file with no project above it was run or hidden, not reported: {rows}")
    CASES.append(
        (
            "a per-project runner runs once in its project, a crate member skips bare rustc, a parent manifest is not a project",
            "verify running cargo, go and tsc from a tree root with no project there, reporting FAIL on a clean change",
        )
    )
    print("  ok    a per-project runner runs once in its project, and a manifest above the repository is not one")


def _placed(files: dict[str, str], target: str, gate: str, argv: list[str], *, repo: bool = True) -> dict:
    """gateplace.placement for one file of a scratch tree, inside a fresh repository unless `repo` is False."""
    import gateplace  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        if repo:
            subprocess.run(["git", "init", "-q", tmp], check=True, timeout=60)
        for rel, body in files.items():
            (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(tmp) / rel).write_text(body)
        return gateplace.placement(str(Path(tmp) / target), gate, argv)


def gate_adoption_cases() -> None:
    """A formatter runs only where the repository adopted it; a tool never reads a dialect it cannot parse.
    MEASURED AT 3.62.0 on 8 public repositories: 31 of 58 FAIL rows were an unadopted formatter, and `jq` on
    a commented devcontainer.json and hadolint on `RUN <<EOF` failed files that were correct."""
    fmt = {
        "no config: prettier proves nothing": ({"a.ts": "x\n"}, "a.ts", ["prettier", "--check"], "prettier"),
        "config in a subfolder adopts it there": (
            {"web/.prettierrc": "{}", "web/a.ts": ""},
            "web/a.ts",
            ["prettier", "--check"],
            None,
        ),
        "package.json naming it adopts it": (
            {"package.json": '{"devDependencies": {"prettier": "3"}}', "a.ts": ""},
            "a.ts",
            ["prettier", "--check"],
            None,
        ),
        "a dependency that only contains the name is not it": (
            {"package.json": '{"x": "eslint-config-prettier"}', "a.ts": ""},
            "a.ts",
            ["prettier", "--check"],
            "prettier",
        ),
        ".editorconfig alone is no adoption": (
            {".editorconfig": "[*.sh]\nindent_size = 2\n", "a.sh": ""},
            "a.sh",
            ["shfmt", "-d"],
            "shfmt",
        ),
        "an .editorconfig key only shfmt reads adopts shfmt": (
            {".editorconfig": "[*.sh]\nswitch_case_indent = true\n", "a.sh": ""},
            "a.sh",
            ["shfmt", "-d"],
            None,
        ),
        "a shfmt key adopts no other formatter": (
            {".editorconfig": "[*.sh]\nswitch_case_indent = true\n", "a.ts": ""},
            "a.ts",
            ["prettier", "--check"],
            "prettier",
        ),
        "a workflow naming it adopts it": (
            {".github/workflows/ci.yml": "run: shfmt -d .\n", "a.sh": ""},
            "a.sh",
            ["shfmt", "-d"],
            None,
        ),
        "[tool.ruff] adopts ruff format": (
            {"pyproject.toml": "[tool.ruff]\nline-length = 99\n", "a.py": ""},
            "a.py",
            ["ruff", "format", "--check"],
            None,
        ),
        "a toolchain's own formatter always runs": ({"a.rs": ""}, "a.rs", ["rustfmt", "--check"], None),
    }
    for name, (files, target, argv, why) in fmt.items():
        placed = _placed(files, target, "formatter", argv)
        if (why is None) != ("why" not in placed) or why and why not in placed["why"]:
            raise SystemExit(f"FAIL formatter adoption, {name}: {placed}")
    if "no repository" not in _placed({"a.ts": ""}, "a.ts", "formatter", ["prettier", "--check"], repo=False).get(
        "why", ""
    ):
        raise SystemExit("FAIL a file in no repository was handed to a repository's chosen formatter")
    import gateplace  # noqa: PLC0415

    here = Path.cwd()
    with tempfile.TemporaryDirectory() as outside:  # `headron check` from an install: no repository at the cwd
        os.chdir(outside)
        try:
            off_tree = gateplace.placement("scripts/doctor.py", "formatter", ["ruff", "format", "--check"])
        finally:
            os.chdir(here)
    if "why" in off_tree:
        raise SystemExit(f"FAIL a tree-relative path read from outside the tree lost its repository: {off_tree}")
    dialects = {
        "a commented JSON file is JSONC": ("x.json", '{\n  // note\n  "a": 1,\n}\n', ["jq", "empty"], "JSONC"),
        "strict JSON still runs jq": ("x.json", '{"a": 1}\n', ["jq", "empty"], None),
        "JSON broken in every reader still runs jq": ("x.json", '{"a": \n', ["jq", "empty"], None),
        "a RUN heredoc is not for hadolint": (
            "Dockerfile",
            "FROM alpine\nRUN <<EOF\necho hi\nEOF\n",
            ["hadolint", "--failure-threshold", "error"],
            "heredoc",
        ),
        "a here-string is no heredoc": (
            "Dockerfile",
            "FROM alpine\nRUN cat <<<'hi'\n",
            ["hadolint", "--failure-threshold", "error"],
            None,
        ),
    }
    for name, (target, body, argv, why) in dialects.items():
        placed = _placed({target: body}, target, "compiler_or_typechecker", argv)
        if (why is None) != ("why" not in placed) or why and why not in placed["why"]:
            raise SystemExit(f"FAIL dialect, {name}: {placed}")
    CASES.append(
        (
            f"a formatter runs only where the repository adopts it ({len(fmt) + 1} trees)",
            "prettier, shfmt, taplo or ruff reporting FAIL on a repository that never chose that style",
        )
    )
    CASES.append(
        (
            f"jq skips only JSONC and hadolint only a heredoc; a file broken everywhere still runs ({len(dialects)} files)",
            "a gate reporting FAIL on a dialect its tool cannot read, or a broken file hidden as unreadable",
        )
    )
    print("  ok    a formatter runs only where adopted, and a tool never reads a dialect it cannot parse")


def consumer_check_cases() -> None:
    """`check` in a consumer's checkout answers for that tree and writes nothing; Headron's contract is not its."""
    import json  # noqa: PLC0415

    def probe(repo: str, *flags: str) -> tuple[int, str]:
        argv = [sys.executable, str(ROOT / "scripts" / "atlas.py"), "check", *flags]
        done = subprocess.run(argv, cwd=repo, capture_output=True, text=True, timeout=600, check=False)
        return done.returncode, done.stdout + done.stderr

    def answers(repo: str) -> str | None:
        status = ["git", "-C", repo, "status", "--porcelain", "--ignored"]
        before = subprocess.run(status, capture_output=True, text=True, timeout=60, check=True).stdout
        rc, said = probe(repo)
        if rc != 0 or "NOT RUN here" not in said:  # first, so a removed branch never reaches --fix on this tree
            return f"check exited {rc}: {said[-300:]}"
        (fix_rc, _), (json_rc, out) = probe(repo, "--fix"), probe(repo, "--json")
        record = json.loads(out) if json_rc == 0 and out.lstrip().startswith("{") else {}
        after = subprocess.run(status, capture_output=True, text=True, timeout=60, check=True).stdout
        if fix_rc != 2:
            return f"check --fix exited {fix_rc} in a consumer"
        if record.get("exit") != 0 or [f["severity"] for f in record.get("findings", [])] != ["warning"]:
            return f"check --json gave {json_rc}: {out[-300:]}"
        return None if before == after else f"check wrote into the consumer's tree: {after}"

    with tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True, timeout=60)
        (Path(repo) / "app.py").write_text("print(1)\n")
        if problem := answers(repo):
            raise SystemExit(f"FAIL {problem}")
        with mutated(
            "scripts/atlas.py", lambda s: s.replace("if (rc := consumer_check(", "if None is (rc := consumer_check(", 1)
        ):
            if answers(repo) is None:
                raise SystemExit("FAIL the consumer check case passed with the consumer branch removed")
    CASES.append(
        (
            "check in a consumer's checkout answers for that tree, refuses --fix and writes nothing",
            "a consumer checkout failing on Headron's own contract and its locked dependencies (polyglot benchmark)",
        )
    )
    print("  ok    check in a consumer's checkout answers for that tree, refuses --fix and writes nothing")


def consumer_gate_cases() -> None:
    """A consumer's changed file is proven by the gates the atlas routes for it, run in its own tree."""
    import branchstate  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as repo:
        (Path(repo) / "bad.py").write_text("def broken(:\n")
        (Path(repo) / "notes.md").write_text("# notes\n")
        runnable, notes = branchstate.consumer_gates(Path(repo), ["bad.py", "notes.md"], "source_change")
        parse = [argv for argv, _ in runnable if "ast.parse" in " ".join(argv)]
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
    """`headron failures --for` hands the shapes relevant to a change, and nothing when none is (3.41.0)."""
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
        "skills/headron/SKILL.md", lambda s: re.sub(r"^description: .+$", long_description, s, count=1, flags=re.M)
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
        tag_at = source.find("tag_rescue(branch, _git)")
        rebase_at = source.find('["git", "rebase", f"origin/{base}"]')
        return 0 <= tag_at < rebase_at

    if not tagged_first():
        raise SystemExit("FAIL the rescue tag is missing or runs after the rebase it exists to survive")
    # THE GUARD RUNS INSIDE THE PLANT: this case once only checked that its own replace applied, so it
    # proved the mutation and nothing about the ordering check.
    with mutated("scripts/branchstate.py", lambda s: s.replace("{tag_rescue(branch, _git)}", "{branch}", 1)):
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
    planted = "HEADRON_" + "PLANTED_INPUT"
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
            "  NO_COLOR: {why:", "  HEADRON_NOTHING_READS_THIS: {why: x, set_by: x, absent: x}\n  NO_COLOR: {why:", 1
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
