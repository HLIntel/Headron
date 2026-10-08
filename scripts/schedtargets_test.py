"""Planted host cases: the scheduler sweep (3.48.0) and each host shape (3.47.0), every one killing a named wrong implementation."""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(module) -> None:
    """A scheduled job whose target is gone FAILS on the host that runs it; a paused one warns (3.48.0)."""
    import schedtargets

    mac = schedtargets.MAC_HOME
    home = Path(tempfile.mkdtemp(prefix="thea-sched-"))
    try:
        (home / "live").mkdir()
        (home / ".hermes" / "scripts").mkdir(parents=True)
        (home / ".hermes" / "cron").mkdir()

        def sweep(jobs: list[dict], platform: str = "darwin") -> dict:
            (home / ".hermes" / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
            return schedtargets.sweep(str(home), platform, str(home / ".hermes"), fixture=True)

        def script(name: str, body: str) -> dict:
            (home / ".hermes" / "scripts" / name).write_text(body, encoding="utf-8")
            return {"name": name, "script": name}

        rows = [
            ("a live $HOME target passes", [script("ok.sh", 'cd "$HOME/live" || exit 1')], "darwin", 0, 0),
            ("a deleted repository FAILS", [script("gone.sh", "cd $HOME/gone || exit 1")], "darwin", 1, 0),
            (
                "a cd that exits zero on a dead target FAILS",
                [script("green.sh", "cd $HOME/live || exit 0")],
                "darwin",
                1,
                0,
            ),
            (
                "a macOS home path on linux FAILS",
                [{"name": "mac", "prompt": f"run {mac}x/y.sh", "workdir": f"{mac}x"}],
                "linux",
                1,
                0,
            ),
            ("a paused dead job only WARNS", [{**script("p.sh", "cd ~/gone"), "state": "paused"}], "darwin", 0, 1),
        ]
        for name, jobs, platform, faults, warns in rows:
            got = sweep(jobs, platform)
            if (bool(got["faults"]), bool(got["warns"])) != (bool(faults), bool(warns)) or not got["checked"]:
                raise SystemExit(f"FAIL {name}: {got}")
            module.CASES.append((name, "a scheduled job reporting success over a target that is not there"))
            print(f"  ok    {name}")
        units = home / ".config" / "systemd" / "user"
        (units / "timers.target.wants").mkdir(parents=True)
        (units / "job.service").write_text("[Service]\nExecStart=%h/nope/run.sh\n", encoding="utf-8")
        (units / "timers.target.wants" / "job.timer").write_text("", encoding="utf-8")
        (home / ".hermes" / "cron" / "jobs.json").unlink()
        got = schedtargets.sweep(str(home), "linux", str(home / ".hermes"), fixture=True)
        if got["jobs"] != 1 or not got["faults"]:
            raise SystemExit(f"FAIL a timer-armed unit with a missing program did not fail: {got}")
        module.CASES.append(
            ("a timer-armed unit with a missing program FAILS", "a unit nobody resolved, not being a job list")
        )
        shutil.rmtree(home / ".config")
        if schedtargets.main(["--root", str(home), "--platform", "linux"]) != 1:
            raise SystemExit("FAIL an empty roster passed")
        module.CASES.append(("an empty scheduler roster FAILS", "a clean pass over nothing"))
        print("  ok    a timer-armed unit with a missing program FAILS; an empty roster FAILS")
    finally:
        shutil.rmtree(home, ignore_errors=True)
    host_shape_cases(module)


def host_shape_cases(module) -> None:
    """Each host shape planted in a record is refused, its clean twin passes; a disabled enforcer fails (3.47.0)."""
    import sys

    import hostshape as hs
    import resilience
    import verify

    now, ok = 1e6, {"budget_tokens": 40000, "measured_tokens": 30000, "measured_at": 1e6 - 3600}
    steps = [{"worker": "w", "step": "a", "state": "begin"}, {"worker": "w", "step": "a", "state": "verified"}]
    change, probe = (
        {"kind": "change", "subject": "m", "at": 1},
        {"kind": "probe", "subject": "m", "at": 2, "passed": True},
    )
    attempts: list[int] = []

    def hang() -> None:
        raise TimeoutError(attempts.append(1))

    with contextlib.suppress(TimeoutError):
        resilience.call(hang, attempts=3, base=0, cap=0, deadline=60, sleep=lambda _: None, interactive=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel, size in (("stub", 500), ("real", 20000), ("cache/gguf/Modelfile", 9), ("cache/uv/p/m.py", 9)):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(b"\0" * size)
            (root / rel).chmod(0o755)
        sweep = [hs.sweep_errors([root / d], ["Modelfile", "*.py"], ["uv"], 1000) for d in ("cache", "cache/uv")]
        stub, real = (hs.binary_errors(root / b, 16384) for b in ("stub", "real"))
        (root / hs.JOURNAL).write_text('{"worker": "w", "step": "a", "state": "begin"}\n{not json}\n')
        journal = hs.read_journal(root), hs.journal_resume_errors(root), hs.journal_snapshot_errors(root, False)
        live = [*steps, {"worker": "w", "step": "b", "state": "begin"}]
        (root / "c").mkdir()
        (root / "c" / hs.JOURNAL).write_text("".join(json.dumps(e) + "\n" for e in live))
        compacted = hs.compact_journal(root / "c"), hs.journal_resume_errors(root / "c")
        (root / "corrupt.json").write_text("{")
        json_arg = subprocess.run(
            [sys.executable, str(module.ROOT / "scripts" / "hostshape.py"), "baseline", str(root / "corrupt.json")],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    rows = [
        (
            "a harness first turn over its budget, or measured long ago, is refused",
            "a fixed context that grows unmeasured",
            hs.baseline_errors({"harnesses": {"h": ok | {"measured_tokens": 50000, "measured_at": 0}}}, now, 26),
            hs.baseline_errors({"harnesses": {"h": ok}}, now, 26),
            "against a budget",
        ),
        (
            "a timeout from an interactive surface is BLOCKED and never retried",
            "a blind retry behind a native dialog",
            [f"{resilience.classify(error=TimeoutError(), interactive=True)} after {len(attempts)}"],
            [] if resilience.classify(error=TimeoutError()) == "transient" else ["x"],
            "blocked after 1",
        ),
        (
            "a step begun and never verified is named on resume, and survives the journal's compaction",
            "a partial write resumed as if finished, or a step journal that grows with every step ever taken",
            hs.resume_errors(live) if compacted == (2, hs.resume_errors(live)) else [],
            hs.resume_errors(steps),
            "w:b",
        ),
        (
            "a snapshot refuses while a writer is mid-step",
            "a snapshot that commits in-flight edits",
            hs.snapshot_errors([{"worker": "x", "step": "e", "state": "begin"}], False),
            hs.snapshot_errors(steps, False),
            "in flight",
        ),
        (
            "a stub binary left by an update is refused",
            "a placeholder binary read as installed",
            stub,
            real,
            "placeholder",
        ),
        (
            "a change with only a version probe after it is refused",
            "a model or tool change shipped without an eval",
            hs.change_probe_errors([change, probe | {"probe": "version"}]),
            hs.change_probe_errors([change, probe | {"probe": "capability"}]),
            "only version",
        ),
        (
            "lanes past the unpushed bound fail the session-end verify",
            "a breach printed and never gated",
            [_lane_row(verify)["verdict"]],
            [],
            "FAIL",
        ),
        (
            "staged application state in a notes repository is refused",
            "editor plugins and caches committed as notes",
            hs.app_state_errors([".app/plugins/x.js", "a.md"], [".*/plugins/*"]),
            hs.app_state_errors(["a.md"], [".*/plugins/*"]),
            ".app",
        ),
        (
            "a work tree that contains the home directory is refused, and a probe with no answer too",
            "a repository at home that a commit sweeps keys into",
            hs.home_repo_errors(Path("/h/u"), "/h/u")
            + hs.home_repo_errors(Path("/h/u"), "/")
            + hs.home_repo_errors(Path("/h/u"), None),
            hs.home_repo_errors(Path("/h/u"), "") + hs.home_repo_errors(Path("/h/u"), "/h/u/p"),
            "inside the work tree rooted at /h/u",
        ),
        (
            "a second instance of a declared singleton is refused",
            "two claimants of one queue",
            hs.singleton_errors([{"pid": 1, "command": "d serve"}, {"pid": 2, "command": "d serve"}], {"d": "d serve"}),
            hs.singleton_errors([{"pid": 1, "command": "d serve"}], {"d": "d serve"}),
            "2 instances",
        ),
        (
            "a tool whose roots follow its cwd is refused",
            "a filesystem tool rooted at cwd, not config",
            hs.root_drift_errors(["/data"], {"/data/x": ["/data"], "/elsewhere": ["/elsewhere"]}),
            hs.root_drift_errors(["/data"], {"/data/x": ["/data"], "/elsewhere": ["/data"]}),
            "differ from configured",
        ),
        (
            "a prompt-only chat template is refused",
            "a rebuild that drops the chat template",
            hs.chat_template_errors("{{ .Prompt }}"),
            hs.chat_template_errors("<|user|>{{ .Prompt }}<|bot|>"),
            "raw prompt",
        ),
        (
            "a sweep over a source file outside a derivable dir is refused",
            "a cache sweep that deletes the only recipe",
            sweep[0],
            sweep[1],
            "Modelfile",
        ),
        (
            "a malformed journal line is reported while valid entries still reach resume and snapshot",
            "a journal decoder crash that hides both malformed input and an in-flight worker",
            [*journal[0][1], *journal[1], *journal[2]]
            if journal[0][0] == steps[:1] and len(journal[0][1]) == 1
            else [],
            [],
            "journal line 2: malformed JSON",
        ),
        (
            "a corrupt JSON argument exits 2 with one clear error",
            "a traceback or a silent None that lets a bad input evade the host check",
            [json_arg.stderr] if json_arg.returncode == 2 else [],
            [],
            "hostshape: cannot parse JSON input",
        ),
    ]
    for name, kills, planted, clean, needle in rows:
        if not any(needle in str(e) for e in planted) or clean:
            raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  planted: {planted}\n  clean: {clean}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")


def _lane_row(verify) -> dict:
    """A throwaway clone whose one lane holds more unpushed commits than the bound allows."""
    import branchstate
    from atlas_rules_test import _git_in

    with tempfile.TemporaryDirectory() as repo:
        _git_in(repo, "init", "-q", "-b", "main")
        for n in range(7):
            _git_in(repo, "commit", "-q", "--allow-empty", "-m", f"c{n}")
            _ = n or _git_in(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        saved, branchstate._tree = branchstate._tree, lambda: Path(repo).resolve()
        try:
            return verify.unpushed_row()
        finally:
            branchstate._tree = saved
