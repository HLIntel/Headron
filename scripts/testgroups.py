"""Run independent planted groups without losing later diagnostics to one failed fixture."""

import os
import subprocess
import time

import impact


def run_group(module, name, run):
    # RECORDED: while the test-impact recorder is armed, every repository file this group loads is
    # its dependency; a passing group is stored on those files' bytes, so the fast loop runs only the
    # groups a change can reach. Unarmed (and before Python 3.12), enter and leave do nothing.
    impact.enter()
    began, ok = time.perf_counter(), False
    try:
        run(module)
        ok = True
    except (Exception, SystemExit) as exc:
        # Do not record a passing CASE for a group that did not finish. The
        # outer harness fails before its successful-case count is evaluated.
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            detail += ": " + str(exc.stderr or exc.stdout or "no diagnostic")[-1000:]
        failures = getattr(module, "SUITE_ERRORS", None)
        if failures is None:
            failures = module.SUITE_ERRORS = []
        failures.append(f"{name}: {detail}")
        print(f"FAIL group {name}: {detail}; continuing independent groups")
    finally:
        impact.leave(name, ok, time.perf_counter() - began)


def run_counted(module, cases, runner) -> None:
    """Promote an independently counted suite only after all of its cases passed."""
    cases.clear()
    runner()
    module.CASES.extend(cases)


def finish_suite(module, expected):
    impact.save()  # every passing group's record, failed or not elsewhere: a failed group's record is dropped
    if failures := getattr(module, "SUITE_ERRORS", []):
        print("\n".join(f"FAIL {failure}" for failure in failures))
        return 1
    if len(module.CASES) != expected:
        raise SystemExit(
            f"CASE COUNT MOVED: {len(module.CASES)} ran, {expected} expected — a harness that silently skips cases prints a full pass"
        )
    print(f"atlas tests: {len(module.CASES)}/{expected} pass")
    module.edges.coverage(len(module.CASES))
    print("SCOPE: these test the CONTRACT. Whether a declared tool EXISTS and RUNS is")
    print("       `python scripts/packprobe.py --mode smoke`; whether the live GitHub controls")
    print("       match the declaration is `python scripts/ghaudit.py`. Neither is left to prose.")
    return 0


# THE PLANTED SUITE'S SHARDS. ATLAS_SHARD picks which half one process runs; CI runs each half as its own job on its
# own checkout, so their plants never meet. The pinned total is the sum of the two shard pins. GUARDS_CASES is
# measured by running that shard alone, never intended.
SHARDS = ("all", "core", "guards")
GUARDS_CASES = 420  # 388 + 1 pre-push fast-forward + 11 receipt_test + 8 seats_test + 1 pricing-term leak + 2 pretooluse + 9 cilocal_test


def shard_name() -> str:
    name = os.environ.get("ATLAS_SHARD", "all")
    if name not in SHARDS:
        raise SystemExit(f"ATLAS_SHARD={name!r} is not one of {SHARDS}")
    return name


def shard_pin(name: str, cross_checked: bool) -> int:
    # 509: +1 MCP prompt refusal, +2 typed-tool and portability cases in mcp_test, +1 failure-row closed-key case in signature_test, +1 pre-push fast-forward case in guards; 520: +11 receipt cases in receipt_test; 528: +8 seats cases in seats_test; 541: +1 THEA_MCP_VERBS grant case in mcp_test
    base = {"all": 541, "core": 541 - GUARDS_CASES, "guards": GUARDS_CASES}[name]
    return base + int(cross_checked)
