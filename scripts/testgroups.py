"""Run independent planted groups without losing later diagnostics to one failed fixture."""

import subprocess


def run_group(module, name, run):
    try:
        run(module)
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


def finish_suite(module, expected):
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
