"""Run independent planted groups without losing later diagnostics to one failed fixture."""

import os
import subprocess
import time
from collections.abc import Callable
from types import ModuleType, SimpleNamespace
from typing import TypeVar

import impact

# A group is handed the suite module, or the SimpleNamespace fake a standalone run stands in for it.
Harness = TypeVar("Harness", ModuleType, SimpleNamespace)


def scrub_git_env() -> None:
    """Drop git's repository-local variables: a hook exports GIT_DIR, and a fixture's `git -C <tmp>` obeys it over -C."""
    listed = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True, timeout=60, check=False
    )
    for name in listed.stdout.split():
        os.environ.pop(name, None)


def repo_settings() -> str:
    """What no fixture may reach: a stray core.bare stops every worktree, a stray user.* misattributes every commit."""
    return subprocess.run(
        ["git", "-C", str(impact.ROOT), "config", "--local", "--get-regexp", r"^(core\.(bare|worktree)|user\.)"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    ).stdout


def _group_failed(module: Harness, name: str, detail: str) -> None:
    vars(module).setdefault("SUITE_ERRORS", []).append(f"{name}: {detail}")
    print(f"FAIL group {name}: {detail}; continuing independent groups")


def run_group(module: Harness, name: str, run: Callable[[Harness], object]):
    # RECORDED: while the test-impact recorder is armed, every repository file this group loads is
    # its dependency; a passing group is stored on those files' bytes, so the fast loop runs only the
    # groups a change can reach. Unarmed (and before Python 3.12), enter and leave do nothing.
    impact.enter()
    settings, began, ok = repo_settings(), time.perf_counter(), False
    try:
        run(module)
        ok = True
    except (Exception, SystemExit) as exc:
        # Do not record a passing CASE for a group that did not finish. The
        # outer harness fails before its successful-case count is evaluated.
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            detail += ": " + str(exc.stderr or exc.stdout or "no diagnostic")[-1000:]
        _group_failed(module, name, detail)
    finally:
        if repo_settings() != settings:
            ok = False
            _group_failed(module, name, "REWROTE THIS REPOSITORY'S core.bare, core.worktree or user.*; restore them")
        impact.leave(name, ok, time.perf_counter() - began)


def run_counted(module: ModuleType, cases: list, runner: Callable[[], object]) -> None:
    """Promote an independently counted suite only after all of its cases passed."""
    cases.clear()
    runner()
    module.CASES.extend(cases)


def split_moved(guards_ran: int | None) -> str | None:
    """Why the whole suite's split disagrees with the guards pin; a total alone only fails later, in a shard job."""
    if guards_ran is None or guards_ran == GUARDS_CASES:
        return None
    return (
        f"SHARD SPLIT MOVED: {guards_ran} guards cases ran, {GUARDS_CASES} pinned — the guards shard would fail at land"
    )


def part_moved(module: ModuleType, part: int, ran: int) -> str | None:
    """Why one guards half's count disagrees with its pin, or None.

    A FAILED GROUP IS NOT A MOVED SPLIT: its cases are never promoted, so the half falls short for a reason
    `finish_suite` names. Reporting the split first hid that reason (a host identity refusal read as a
    moved split), so a half with recorded failures defers to `finish_suite`.
    """
    expected = shard_pin(f"guards-{part}", False)
    if ran == expected or getattr(module, "SUITE_ERRORS", []):
        return None
    return f"SHARD SPLIT MOVED: guards-{part} ran {ran}, expected {expected}"


def host_skipped(module: ModuleType, cases: int, why: str) -> None:
    """Cases this host cannot run (no toolchain): named, counted apart from passes, refused in CI.

    THE PIN MUST NOT DEPEND ON THE MACHINE: a host without `go` ran 4 fewer cases and read as a moved
    split. CI declares every toolchain, so a skip there is a FAIL, never a quieter pin.
    """
    if os.environ.get("CI"):
        raise SystemExit(f"FAIL {cases} cases did not run in CI: {why}")
    vars(module).setdefault("HOST_SKIPS", []).append((cases, why))
    print(f"  skip  {cases} cases not run on this host: {why}")


def counted(module: ModuleType) -> int:
    """Cases that passed plus cases this host named as not runnable: what the pins are compared with."""
    return len(module.CASES) + sum(n for n, _ in getattr(module, "HOST_SKIPS", []))


def run_guard_halves(module: ModuleType, run_half: Callable[[int], object]) -> None:
    """Run both guards halves in one process, refusing a half whose count moved for no recorded failure."""
    for part in (0, 1):
        before = counted(module)
        run_half(part)
        if moved := part_moved(module, part, counted(module) - before):
            raise SystemExit(moved)


def finish_suite(module: ModuleType, expected: int, guards_ran: int | None = None):
    impact.save()  # every passing group's record, failed or not elsewhere: a failed group's record is dropped
    if failures := getattr(module, "SUITE_ERRORS", []):
        print("\n".join(f"FAIL {failure}" for failure in failures))
        # Record test run failure for session-to-session benefits
        try:
            import agents  # noqa: PLC0415

            agents.record_test_run(0, expected, 0, False)
        except Exception:  # noqa: S110
            pass  # fails open: never block the suite on a ledger write
        return 1
    if counted(module) != expected:
        raise SystemExit(
            f"CASE COUNT MOVED: {counted(module)} ran, {expected} expected — a harness that silently skips cases prints a full pass"
        )
    if moved := split_moved(guards_ran):
        raise SystemExit(moved)
    skips = getattr(module, "HOST_SKIPS", [])
    host = "".join(f"; {n} not run on this host ({why})" for n, why in skips)
    print(f"atlas tests: {len(module.CASES)}/{expected} pass{host}")
    module.edges.coverage(len(module.CASES))
    # Record test run success for session-to-session benefits
    try:
        import agents  # noqa: PLC0415

        agents.record_test_run(len(module.CASES), expected, 0, True)
    except Exception:  # noqa: S110
        pass  # fails open: never block the suite on a ledger write
    print("SCOPE: these test the CONTRACT. Whether a declared tool EXISTS and RUNS is")
    print("       `python scripts/packprobe.py --mode smoke`; whether the live GitHub controls")
    print("       match the declaration is `python scripts/ghaudit.py`. Neither is left to prose.")
    return 0


# THE PLANTED SUITE'S SHARDS. ATLAS_SHARD picks which half one process runs; CI runs each half as its own job on its
# own checkout, so their plants never meet. The pinned total is the sum of the two shard pins. GUARDS_CASES is
# measured by running that shard alone, never intended.
SHARDS = ("all", "core", "guards", "guards-0", "guards-1")
GUARD_PARTS = (230, 277)
GUARDS_CASES = sum(GUARD_PARTS)


def shard_name() -> str:
    name = os.environ.get("ATLAS_SHARD", "all")
    if name not in SHARDS:
        raise SystemExit(f"ATLAS_SHARD={name!r} is not one of {SHARDS}")
    return name


def shard_pin(name: str, cross_checked: bool) -> int:
    base = {
        "all": 668,
        "core": 668 - GUARDS_CASES,
        "guards": GUARDS_CASES,
        "guards-0": GUARD_PARTS[0],
        "guards-1": GUARD_PARTS[1],
    }[name]
    return base + int(cross_checked)


def micro_shreds(groups_list: tuple[str, ...] | list[str], slice_index: int, total_slices: int) -> list[str]:
    """Micro-shred a test group list into fine-grained partitions for parallel execution or targeted verification.

    Permits shredding large test rosters (e.g. 36 planted groups) into micro-slices,
    spreading execution across workers with deterministic assignment.
    """
    if total_slices < 1 or slice_index < 0 or slice_index >= total_slices:
        raise ValueError(f"invalid micro-shred slice {slice_index}/{total_slices}")
    return [name for idx, name in enumerate(groups_list) if idx % total_slices == slice_index]
