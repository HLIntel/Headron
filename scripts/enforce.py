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
  install                    add a pre-commit hook that runs `check --staged`, chaining any hook already there
  uninstall                  remove it and restore the hook install moved aside
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
from atlascore import ROOT, atlas, route_for, tracked, worktree  # noqa: E402

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
    # GLOBBED, not compared: `*.?sproj` can never be an exact filename, and a literal name globs
    # to itself, so this is strictly wider than the equality it replaces.
    return next((d for d in path.resolve().parents if next(d.glob(marker), None)), None) if marker else None


def _planted_failure(path: Path) -> str:
    """The declared reason this file's failure is the ARTIFACT, or "" when it is an ordinary file.

    Read from atlas.yaml/enforcement/planted_failure_paths so the prefix and its reason travel together;
    a prefix list inside this file would age where nobody looks.
    """
    prefixes = (atlas().get("enforcement") or {}).get("planted_failure_paths") or {}
    # RELATIVE TO THE ROOT, ALWAYS. The declared prefixes are repository-relative and callers hand this
    # function both shapes: `--staged` yields relative paths and `--tracked` yields absolute ones, so
    # comparing the raw path silently matched nothing for one of the two and the fixtures came back
    # refused. Measured at 3.32.0: 0 refused on relative paths, 4 on absolute, same tree.
    try:
        text = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        text = path.as_posix()
    return next((str(reason) for prefix, reason in prefixes.items() if text.startswith(str(prefix))), "")


def _undecided(tool: str, code: int) -> str:
    """The declared reason this exit code means the tool DECIDED NOTHING, or "" when it decided."""
    spec = (atlas().get("enforcement") or {}).get("undecided_exits") or {}
    codes = spec.get(tool.rsplit("/", 1)[-1]) or []
    return str(spec.get("reason") or "could not decide") if code in [int(c) for c in codes] else ""


def shebang_argv(path: Path, route: str) -> list[str] | None:
    """The checker for the interpreter a file's first line NAMES, when that is not its suffix's route.

    A SUFFIX NAMES A FAMILY; THE SHEBANG NAMES WHO RUNS IT (3.43.0). `.sh` routes to bash, and 19 zsh
    scripts in a consumer were refused by `bash -n` for zsh syntax — refused for being correct.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return None
    words = first[2:].split() if first.startswith("#!") else []
    name = Path(words[0]).name if words else ""
    if name == "env" and len(words) > 1:
        name = words[1]
    table = (atlas().get("enforcement") or {}).get("shebang_checkers") or {}
    return [str(a) for a in table[name]] if name != route and isinstance(table.get(name), list) else None


def check_file(path: Path) -> tuple[str, str]:
    """(PASS|FAIL|SKIP, detail) for one file."""
    planted = _planted_failure(path)
    if planted:
        return "SKIP", f"a planted failure by declaration: {planted[:90]}"
    route = route_for(str(path))
    if not route:
        return "SKIP", "no route"
    # A ROUTE IS GUIDANCE; A SUFFIX IS SOURCE. `route_for` resolves a path by its directory too, which
    # is right for "which guide do I read" and wrong for "which compiler runs on it" — so `docs/PYTHON.md`
    # resolved to python and was fed to the AST parser, and `languages/rust/README.md` to rustc. MEASURED
    # at 3.32.0: 22 documents refused for not being source, which is why this rung could never be wired
    # into a hook. The suffix map in artifact_routes is the identity, and it excludes exactly 117 routed
    # files — 80 .md, 36 .yaml, 1 .jsonc — and not one source file.
    declared_route = (atlas().get("artifact_routes") or {}).get(path.suffix)
    if declared_route != route:
        return "SKIP", (f"{path.suffix or 'no suffix'} is not declared source for route {route!r} "
                        f"(artifact_routes says {declared_route!r}) — its route is guidance, not a compiler")
    verdict = gate_resolution(route, "compiler_or_typechecker")
    argv = shebang_argv(path, route) or verdict.get("argv")
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
        # COULD NOT DECIDE IS NOT DECIDED NO. This rung's own docblock says SKIP IS NOT PASS; the same
        # rule runs the other way, and pytest's exit 5 ("no tests collected") was read as a refusal.
        undecided = _undecided(argv[0], done.returncode)
        if undecided:
            return "SKIP", f"{argv[0]} exited {done.returncode} and decided nothing: {undecided[:90]}"
        tail = (done.stderr or done.stdout).strip().splitlines()
        return "FAIL", f"{' '.join(argv)}: {tail[-1][:120] if tail else f'exited {done.returncode}'}"
    return "PASS", " ".join(argv)


def staged() -> list[Path]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],  # noqa: S607
                         capture_output=True, text=True, check=True, timeout=600).stdout
    return [Path(p) for p in out.splitlines() if p]


def tracked_here() -> list[Path]:
    """Every file the CALLER's repository tracks. `tracked()` lists the atlas's own tree, so a consumer
    running `check --tracked` swept Thea's 401 files and passed (3.42.0) — the landing shape again."""
    tree = worktree()
    if tree == ROOT.resolve():
        return sorted(tracked())
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=tree, timeout=600)  # noqa: S607
    return sorted(tree / p for p in raw.decode().split("\0") if p)


TEST_NAME = r"(^test_.*\.py$|_test\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|\.bats$)"


def test_file(path: Path) -> tuple[str, str] | None:
    """Run a staged TEST file under its pack's runner, when that runner takes one file — else None."""
    import re  # noqa: PLC0415
    route = route_for(str(path))
    if not route or not re.search(TEST_NAME, path.name):
        return None
    argv = gate_resolution(route, "unit_tests").get("argv") or []
    runners = ((atlas().get("gate_tools") or {}).get("unit_tests") or {}).get("per_file_runners") or []
    if not argv or argv[0] not in runners or not shutil.which(argv[0]):
        return None
    try:
        done = subprocess.run([*argv, str(path)], capture_output=True, text=True, timeout=TIMEOUT, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        return "FAIL", f"{argv[0]} {path} timed out"
    tail = (done.stdout + done.stderr).strip().splitlines()
    if done.returncode == 0:
        return "PASS", f"{argv[0]} {path}"
    # COULD NOT DECIDE IS NOT DECIDED NO, and this is where it bit: six harnesses here are named
    # *_test.py and are standalone programs with their own main, not pytest suites, so pytest collected
    # nothing, exited 5, and the rung called every one of them refused. The file's own docblock already
    # said SKIP IS NOT PASS; the rule runs the other way too.
    undecided = _undecided(argv[0], done.returncode)
    if undecided:
        return "SKIP", f"{argv[0]} exited {done.returncode} and decided nothing: {undecided[:90]}"
    return "FAIL", f"{argv[0]}: {tail[-1][:120] if tail else done.returncode}"


def check(paths: list[Path]) -> int:
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    absent = 0
    for path in paths:
        state, detail = check_file(path)
        if state == "PASS":
            state, detail = test_file(path) or (state, detail)
        counts[state] += 1
        absent += 1 if state == "SKIP" and "not installed here" in detail else 0
        if state != "PASS":
            print(f"{state:<5} {path}  {detail}")
    # THE COVERAGE LINE NAMES ITS OWN BLIND SPOT (3.32.1). A clean pass here was read as a verdict and
    # was not one: this machine has no dotnet, so it SKIPPED an F# script that CI fed to `dotnet build`,
    # which refused it. A skip for an absent toolchain is a question nobody asked, not an answer.
    print(f"thea enforce: {counts['PASS']} passed, {counts['FAIL']} refused, {counts['SKIP']} skipped "
          f"of {len(paths)} file(s) — {absent} skipped for a toolchain this machine does not have, so a "
          f"clean pass here is not a clean pass everywhere")
    return 1 if counts["FAIL"] else 0


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False, timeout=600).stdout.strip()  # noqa: S603, S607


def install() -> int:
    """Install the hook WITHOUT displacing one that is already there (3.10.0).

    It refused whenever a foreign hook existed — including on Thea's own repository. Now, as the pre-commit
    framework does: a repository that uses that framework gets the entry to add and nothing is written; a
    tracked core.hooksPath is refused by name, because that directory is the repository's own code; a plain
    foreign hook is MOVED to pre-commit.legacy (never deleted) and runs first, its failure still blocking.
    """
    if Path(".pre-commit-config.yaml").exists():
        # NOT RUN HERE: the framework was not installed where this was written, so the entry is the framework's
        # documented `repo: local` shape and nothing more is claimed for it.
        print("this repository uses the pre-commit framework; nothing was written. Add under `repos:`:\n"
              f"  - repo: local\n    hooks:\n      - id: thea-enforce\n        name: thea enforce\n"
              f"        entry: {sys.executable} {HERE / 'enforce.py'} check\n        language: system")
        return 0
    hooks_path = _git("config", "core.hooksPath")
    if hooks_path:
        # THE PATH MUST BE REPOSITORY-RELATIVE. It printed an absolute path, and inside a git worktree
        # that path contains the worktree's own name — a line that stops working the day the worktree is
        # removed, pasted into a file that is tracked forever.
        existing = Path(hooks_path) / "pre-commit"
        wanted = "scripts/enforce.py check --staged"
        if existing.is_file() and wanted in existing.read_text(encoding="utf-8"):
            print(f"already installed: {hooks_path}/pre-commit runs `{wanted}`")
            return 0
        print(f"REFUSED: core.hooksPath is {hooks_path} — a tracked hooks directory is this repository's "
              f"own code and a program must not rewrite it. Add this line to its pre-commit by hand:\n"
              f"  PYTHONPATH=scripts python3 {wanted} || exit 1")
        return 1
    hook = Path(_git("rev-parse", "--git-path", "hooks")) / "pre-commit"
    legacy = hook.with_name("pre-commit.legacy")
    if hook.exists() and "thea enforce" not in hook.read_text(errors="ignore"):
        if legacy.exists():
            print(f"REFUSED: {hook} and {legacy} both exist and neither is Thea's — resolve them by hand")
            return 1
        hook.rename(legacy)
        print(f"moved the existing hook to {legacy}; it runs first and its failure still blocks the commit")
    hook.parent.mkdir(parents=True, exist_ok=True)
    chain = f'[ -x "{legacy}" ] && {{ "{legacy}" "$@" || exit $?; }}\n'
    hook.write_text(f'#!/bin/sh\n# thea enforce — refuses a commit whose file fails its own toolchain\'s check\n'
                    f'{chain}exec "{sys.executable}" "{HERE / "enforce.py"}" check --staged\n')
    hook.chmod(0o755)
    print(f"installed {hook}")
    return 0


def uninstall() -> int:
    """Remove Thea's hook and put back whatever install moved aside — the move is reversible by design."""
    hook = Path(_git("rev-parse", "--git-path", "hooks")) / "pre-commit"
    legacy = hook.with_name("pre-commit.legacy")
    if hook.exists() and "thea enforce" in hook.read_text(errors="ignore"):
        hook.unlink()
    if legacy.exists():
        legacy.rename(hook)
        print(f"restored {hook}")
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
        if argv[1:] == ["--staged"]:
            return check(staged())            # zero staged files is a real, honest zero
        if argv[1:] == ["--tracked"]:
            return check(tracked_here())      # the caller's whole tree, which is what a GATE must sweep
        if not argv[1:]:
            # A BARE `check` SWEPT NOTHING AND EXITED 0 — a vacuous pass, and the one shape this
            # repository refuses everywhere else: refusing 0 of 0 and 0 of many print the same 0.
            print("REFUSED: `check` was given no file. Name files, or --staged for a commit, or "
                  "--tracked to sweep the whole tree.")
            return 2
        return check([Path(p) for p in argv[1:]])
    if argv[:1] == ["install"]:
        return install()
    if argv[:1] == ["uninstall"]:
        return uninstall()
    if argv[:1] == ["measure"]:
        return measure(HERE.parent, record="--record" in argv)
    print(__doc__.split("\n\n", 1)[0])
    print("usage: enforce.py check <files>|--staged|--tracked · install · uninstall · measure")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
