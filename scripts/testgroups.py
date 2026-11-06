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
    if len(module.CASES) != expected:
        raise SystemExit(
            f"CASE COUNT MOVED: {len(module.CASES)} ran, {expected} expected — a harness that silently skips cases prints a full pass"
        )
    if moved := split_moved(guards_ran):
        raise SystemExit(moved)
    print(f"atlas tests: {len(module.CASES)}/{expected} pass")
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
SHARDS = ("all", "core", "guards")
GUARDS_CASES = 462


def shard_name() -> str:
    name = os.environ.get("ATLAS_SHARD", "all")
    if name not in SHARDS:
        raise SystemExit(f"ATLAS_SHARD={name!r} is not one of {SHARDS}")
    return name


def shard_pin(name: str, cross_checked: bool) -> int:
    # 510: +1 MCP prompt refusal, +2 typed-tool and portability cases in mcp_test, +1 failure-row closed-key case in signature_test, +1 pre-push fast-forward case in guards, +1 dependency-pruning case in verifyrun_test; 521: +11 receipt cases in receipt_test; 529: +8 seats cases in seats_test; 542: +1 HEADRON_MCP_VERBS grant case in mcp_test; 559: +16 edge enforcer & promoted invariant cases; 560: +1 GitHub App checkout-preparation case; 561: +1 pack-card Markdown gate case; 562: +1 staged cache invariant case; 563: +1 bytecode-free gate-runner case, counted by cross_checked; 567: +1 land reuse verification case; 568: +1 merge-method case in guards; 569: +1 fast-gate landing case in guards; 570: +1 headline-only-rises case in guards; 571: +1 webhook body-bound case in guards; 575: +2 graph edge completeness cases in decide_test; 576: +1 malformed webhook payload case in guards; 606: +2 full-replay and shard-split cases in guards; 608: +2 git-reach cases in guards
    # +1 a lane entered through the installed CLI is its own atlas (own_checkout_test).
    # +2 an entry surface's first step must run (agreement.documented_command_errors).
    # +3 a documented flag the parser lacks, and verify's promised flags reach verify.py (clihelp_test).
    # +1 a hand-edited first-glance line.
    # +7 who wrote a receipt: a rewritten receipt, a wrong signer, a wrong namespace, a revoked key (receiptsign_test).
    # +2 a backticked name no code defines, in a doc and in a comment (orphans.stale_names).
    # -24 dead code left with its proof: gate_verdict, the graph, .headron rules, the pipeline states, processes.
    base = {"all": 604, "core": 604 - GUARDS_CASES, "guards": GUARDS_CASES}[name]
    return base + int(cross_checked)


def micro_shreds(groups_list: tuple[str, ...] | list[str], slice_index: int, total_slices: int) -> list[str]:
    """Micro-shred a test group list into fine-grained partitions for parallel execution or targeted verification.

    Permits shredding large test rosters (e.g. 36 planted groups) into micro-slices,
    spreading execution across workers with deterministic assignment.
    """
    if total_slices < 1 or slice_index < 0 or slice_index >= total_slices:
        raise ValueError(f"invalid micro-shred slice {slice_index}/{total_slices}")
    return [name for idx, name in enumerate(groups_list) if idx % total_slices == slice_index]
