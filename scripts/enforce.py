#!/usr/bin/env python3
"""The enforcement rung at commit time, for ANY repository and ANY agent: refuse a change whose file fails
its own toolchain's check-only command.

WHY (3.4.0). Thea enforced on itself (its hooks, its CI) and in a consumer's CI (the reusable workflow),
and nowhere at the moment an agent in someone else's repository commits. Read as instructions alone,
Thea is a long system prompt: the agent may skip it. Every agent — Claude, Codex, Cursor, opencode,
Hermes — commits through git, so a git pre-commit hook is the one place all of them pass.

  check <files> | --staged   route each file, run its compiler_or_typechecker command in a scratch
                             directory (so a compiler cannot litter the repository), print
                             PASS / FAIL / SKIP per file; exit 1 on any FAIL
  install                    write a pre-commit hook into the current repository that runs `check --staged`
  measure                    plant a syntax break in each example whose toolchain is installed and count
                             how many breaks `check` refuses — the enforcement rate, printed with its K

SKIP IS NOT PASS. A file with no route, a gate declared absent, or a toolchain not installed is SKIP,
counted and printed, never folded into the pass count. WHAT IT DOES NOT PROVE: that the code is right —
only that it parses and type-checks under its own toolchain. Tests stay with CI, where they can be slow.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agentpolicy import gate_resolution  # noqa: E402
from atlascore import atlas, route_for, tracked  # noqa: E402

TIMEOUT = 120
# A break every check-only command must refuse: an unclosed bracket is invalid in every routed language.
BREAK = "\n)(]\n"


def _listing(folder: Path) -> set[str]:
    """Every file under `folder`, recursively: a .pyc written into an EXISTING __pycache__ is litter too."""
    return {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}


def _marker(argv: list[str]) -> str | None:
    """The file whose directory a per-project checker must run in, or None for a per-file checker."""
    spec = (atlas().get("gate_tools") or {}).get("compiler_or_typechecker") or {}
    return (spec.get("per_directory") or {}).get(" ".join(argv))


def _project_home(path: Path) -> Path | None:
    route = route_for(str(path))
    argv = gate_resolution(route, "compiler_or_typechecker").get("argv") if route else None
    marker = _marker(argv) if argv else None
    return next((d for d in path.resolve().parents if (d / marker).exists()), None) if marker else None


def check_file(path: Path) -> tuple[str, str]:
    """(PASS|FAIL|SKIP, detail) for one file."""
    route = route_for(str(path))
    if not route:
        return "SKIP", "no route"
    verdict = gate_resolution(route, "compiler_or_typechecker")
    argv = verdict.get("argv")
    if not argv:
        return "SKIP", f"{verdict['state']}: {verdict['why'][:80]}"
    if not shutil.which(argv[0]):
        return "SKIP", f"{argv[0]} not installed here"
    marker = _marker(argv)
    home = _project_home(path)
    if marker and home is None:
        return "SKIP", f"{' '.join(argv)} runs per project and no {marker} is above this file"
    before = _listing(path.resolve().parent)
    with tempfile.TemporaryDirectory() as scratch:
        cmd, cwd = ([*argv], home) if home else ([*argv, str(path.resolve())], scratch)
        try:
            done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT, check=False)  # noqa: S603
        except subprocess.TimeoutExpired:
            return "FAIL", f"{' '.join(argv)} timed out"
    # A CHECK MAY NOT LITTER (3.4.0): ocamlopt wrote .cmi/.cmx/.o beside the source it was only checking.
    litter = sorted(_listing(path.resolve().parent) - before)
    if litter and not home:
        return "FAIL", f"{' '.join(argv)} wrote {', '.join(litter[:3])} beside the source — a check must not write"
    if done.returncode != 0:
        tail = (done.stderr or done.stdout).strip().splitlines()
        return "FAIL", f"{' '.join(argv)}: {tail[-1][:120] if tail else f'exited {done.returncode}'}"
    return "PASS", " ".join(argv)


def staged() -> list[Path]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],  # noqa: S607
                         capture_output=True, text=True, check=True, timeout=600).stdout
    return [Path(p) for p in out.splitlines() if p]


def check(paths: list[Path]) -> int:
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for path in paths:
        state, detail = check_file(path)
        counts[state] += 1
        if state != "PASS":
            print(f"{state:<5} {path}  {detail}")
    print(f"thea enforce: {counts['PASS']} passed, {counts['FAIL']} refused, {counts['SKIP']} skipped "
          f"of {len(paths)} file(s)")
    return 1 if counts["FAIL"] else 0


def install() -> int:
    hooks = Path(subprocess.run(["git", "rev-parse", "--git-path", "hooks"],  # noqa: S607
                                capture_output=True, text=True, check=True, timeout=600).stdout.strip())
    hook = hooks / "pre-commit"
    if hook.exists() and "thea enforce" not in hook.read_text(errors="ignore"):
        print(f"REFUSED: {hook} exists and is not Thea's — chain it by hand: python {HERE / 'enforce.py'} check --staged")
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f'#!/bin/sh\n# thea enforce — refuses a commit whose file fails its own toolchain\'s check\n'
                    f'exec "{sys.executable}" "{HERE / "enforce.py"}" check --staged\n')
    hook.chmod(0o755)
    print(f"installed {hook}")
    return 0


def measure(root: Path, record: bool = False) -> int:
    """Plant BREAK into a copy of each example; count how many the check refuses. K is printed."""
    caught = missed = skipped = misfired = 0
    # THE TRACKED TREE, NOT THE DISK: the first run trialled gleam build output and __pycache__.
    for path in sorted(p for p in tracked() if p.relative_to(root).parts[:1] == ("examples",)):
        first = check_file(path)
        if first[0] == "FAIL":
            # A CORRECT FILE REFUSED IS A MISFIRE, never a skip (3.4.0): wrong flags on clang++, swiftc and
            # go vet refused valid examples, and counting them as "not trialled" hid it.
            misfired += 1
            print(f"MISFIRE {path}  {first[1]}")
            continue
        if first[0] != "PASS":
            skipped += 1  # no route, no check-only mode, or no toolchain here
            continue
        with tempfile.TemporaryDirectory() as scratch:
            # A PER-PROJECT TOOL NEEDS ITS PROJECT: copy the directory holding the marker and break the
            # file inside it, or the trial measures "no project found" and reads as a miss.
            home = _project_home(path)
            if home:
                shutil.copytree(home, Path(scratch) / home.name, ignore=shutil.ignore_patterns("build", ".git"))
                broken = Path(scratch) / home.name / path.resolve().relative_to(home)
            else:
                broken = Path(scratch) / path.name
            broken.write_text(path.read_text(encoding="utf-8") + BREAK, encoding="utf-8")
            state, _ = check_file(broken)
        if state == "FAIL":
            caught += 1
        else:
            missed += 1
            print(f"MISSED {path}")
    trials = caught + missed
    if record and trials:
        import json
        languages = sorted({route_for(str(q)) for q in tracked()
                            if q.relative_to(root).parts[:1] == ("examples",) and check_file(q)[0] == "PASS"} - {None})
        (root / "benchmarks" / "enforce-latest.json").write_text(json.dumps({
            "_why": "enforce.py measure: planted syntax breaks refused at commit time, per installed toolchain",
            "measured_at": str(atlas().get("version")), "refused": caught, "planted": trials,
            "not_trialled": skipped, "languages": languages}, indent=2) + "\n", encoding="utf-8")
    print(f"thea enforce measure: refused {caught} of {trials} planted breaks"
          f"{f' ({100 * caught / trials:.0f}%)' if trials else ''}; {skipped} file(s) not trialled "
          "(no route, no check-only mode, or no toolchain here)")
    print(f"thea enforce measure: {misfired} correct file(s) refused (misfires)") if misfired else None
    return 0 if trials and not missed and not misfired else 1


def main(argv: list[str]) -> int:
    if argv[:1] == ["check"]:
        return check(staged() if argv[1:] == ["--staged"] else [Path(p) for p in argv[1:]])
    if argv[:1] == ["install"]:
        return install()
    if argv[:1] == ["measure"]:
        return measure(HERE.parent, record="--record" in argv)
    print(__doc__.split("\n\n", 1)[0])
    print("usage: enforce.py check <files>|--staged · install · measure")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
