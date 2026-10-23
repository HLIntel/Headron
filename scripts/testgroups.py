"""Run independent planted groups without losing later diagnostics to one failed fixture."""

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


def finish_suite(module, expected, coverage=True):
    impact.save()  # every passing group's record, failed or not elsewhere: a failed group's record is dropped
    if failures := getattr(module, "SUITE_ERRORS", []):
        print("\n".join(f"FAIL {failure}" for failure in failures))
        return 1
    if len(module.CASES) != expected:
        raise SystemExit(
            f"CASE COUNT MOVED: {len(module.CASES)} ran, {expected} expected — a harness that silently skips cases prints a full pass"
        )
    print(f"atlas tests: {len(module.CASES)}/{expected} pass")
    if coverage:  # a shard holds part of the cases: --aggregate measures the coverage over all of them
        module.edges.coverage(len(module.CASES))
    print("SCOPE: these test the CONTRACT. Whether a declared tool EXISTS and RUNS is")
    print("       `python scripts/packprobe.py --mode smoke`; whether the live GitHub controls")
    print("       match the declaration is `python scripts/ghaudit.py`. Neither is left to prose.")
    return 0


def shard_arg(argv):
    """`--shard K/N`: this process runs every Nth section, from index K. Absent, it runs the whole suite."""
    if "--shard" not in argv:
        return None
    index, count = (int(x) for x in argv[argv.index("--shard") + 1].split("/"))
    assert 0 <= index < count, f"--shard {index}/{count}: the index must be below the count"
    return index, count


def aggregate(directory, edges, expected) -> int:
    """Merge the shard records: together they must run the whole suite, and coverage is measured over all of it."""
    import json

    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]
    assert records, f"no shard records in {directory}"
    counts = {record["of"] for record in records}
    assert len(counts) == 1, f"shard records disagree on the shard count: {sorted(counts)}"
    assert sorted(record["shard"] for record in records) == list(range(counts.pop())), "a shard did not report"
    for record in records:
        assert record["ran"] == record["expected"], (
            f"shard {record['shard']} ran {record['ran']}, expected {record['expected']}"
        )
        edges.EDGES.update(record["edges"])
    total = sum(record["expected"] for record in records)
    assert total in (expected, expected + 1), f"the shards ran {total}, the unsharded suite is {expected}"
    print(f"atlas tests: {total} cases across {len(records)} shards")
    edges.coverage(total)
    return 0
