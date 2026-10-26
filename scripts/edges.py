"""The test -> declaration edge: every planted case names the enforcer(s) its plant must trip.

WHY (3.50.0). A planted case proved only that the WHOLE check failed and printed a needle, never
which enforcer refused, so a coincidental emitter kept a case green after its own enforcer died.
Naming the enforcer (`case(by=)`) makes that edge a fact the harness checks, and lets the case run
the enforcer alone: MEASURED, a full check per case was 274.2 of 359.0 s of the planted suite.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, cast

import atlas
import packmanifest

LEDGER = "thea-edges.json"  # the last full suite's EDGES, in this clone's git dir
EDGES: dict[str, list[str]] = {}  # case name -> every enforcer it declared and tripped
# Enforcers no planted case names. It may only FALL: a new enforcer arrives with the case naming it.
UNNAMED_ENFORCER_CEILING = 7
# Bounded storage: the ledger is small (case name -> enforcer list), but cap it to prevent unbounded growth.
MAX_LEDGER_BYTES = 128 * 1024  # 128 KiB cap: ~550 cases × ~2 enforcers each, well under the limit


def stages() -> dict:
    """Every enforcer check() is built from, by name. Its keys are the only legal `by=` values."""
    import atlasgen
    import atlasinv
    import roster

    named = {
        (f.__name__ if f.__module__ in ("atlas", "__main__") else f"{f.__module__}.{f.__name__}"): f
        for f in atlas.composed()
    }
    targets = sorted(p.parent.name for p in (atlas.ROOT / "languages").glob("*/tools.yaml"))
    named |= {
        "parse_errors": list,  # preflight runs it for every stage; naming it runs nothing more
        "manifest_errors": lambda: [e for t in targets for e in packmanifest.manifest_errors(t)],
        "dated_claim_errors": lambda: atlas.dated_claim_errors()[0],
        "declaration_errors": lambda: atlas.declaration_errors()[0],
        "generated_errors": lambda: atlas.generated_errors(atlasgen)[0],
        "tracked_file_errors": lambda: atlas.tracked_file_errors()[0],
        "link_errors": lambda: atlas.link_errors()[0],
        "roster.instrument_roster_errors": lambda: roster.instrument_roster_errors()[0],
    }
    return named | {f"inv:{n}": (lambda n=n: atlasinv.invariant_violations(n)) for n in atlasinv.INVARIANT_CHECKS}


def stage_errors(name: str) -> list[str]:
    """Preflight, then ONE named enforcer. A KeyError on an unknown name is the refusal: never a guess."""
    enforcer = stages()[name]
    atlas.atlas.cache_clear()
    packmanifest.reset_caches()
    errors = atlas.parse_errors() + atlas.plant_leftover_errors()
    try:
        atlas.atlas()
    except ValueError as exc:  # the fatal check() reports; no enforcer reads a declaration that is not there
        return [*errors, f"atlas.yaml does not parse: {exc}"]
    return errors + enforcer()


def _staged(by: str) -> tuple[int, str]:
    try:
        found = stage_errors(by)
    except KeyError:
        raise SystemExit(f"FAIL by={by!r} names no enforcer; edges.stages() is the roster") from None
    return (1 if found else 0), "\n".join(f"- {e}" for e in sorted(set(found)))


def named(by) -> list[str]:
    """`by` as a list: one enforcer, or every enforcer a plant trips (a stage and the invariant wrapping it)."""
    return [by] if isinstance(by, str) else list(by)


def verdict(name: str, by, expect_fail: bool, needle: str | None, run_check) -> tuple[int, str]:
    """The (rc, output) a case judges. With `by`, the declared enforcers alone, EACH of which must emit the
    needle; THEA_CASES_FULL=1 runs the whole check as before AND still proves every edge, so the cheap
    route is never the only evidence an edge is real."""
    if not by:
        return run_check()
    if not (expect_fail and needle):
        raise SystemExit(f"FAIL {name}\n  by={by!r} needs a failing plant and a needle: an edge proves who refused")
    staged = [_staged(b) for b in named(by)]
    for b, (_, out) in zip(named(by), staged):
        if needle not in out:
            raise SystemExit(f"FAIL {name}\n  declares by={b!r}, and that enforcer did not emit {needle!r}")
    rc, out = run_check() if os.environ.get("THEA_CASES_FULL") else staged[0]
    EDGES[name] = named(by)  # a case that then fails ends the suite, so a recorded edge is never a false one
    return rc, out


def assert_case(
    name: str, kills: str, expect_fail: bool, needle: str | None = None, by=None, *, run_check, cases
) -> None:
    """Assert a case's verdict and register it only after its declared edge proved real."""
    rc, out = verdict(name, by, expect_fail, needle, run_check)
    failed = rc != 0
    if failed != expect_fail:
        raise SystemExit(
            f"FAIL {name}\n  kills: {kills}\n  rc={rc}, expected {'non-zero' if expect_fail else '0'}\n{out[:800]}"
        )
    if needle and needle not in out:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  expected {needle!r} in output\n{out[:800]}")
    cases.append((name, kills))
    print(f"  ok    {name}")


def judge_ceiling(unnamed: list[str]) -> None:
    if len(unnamed) > UNNAMED_ENFORCER_CEILING:
        raise SystemExit(
            f"EDGE COVERAGE FELL: {len(unnamed)} enforcers no case names, ceiling "
            f"{UNNAMED_ENFORCER_CEILING}: {unnamed[:8]}"
        )


def coverage(cases: int) -> None:
    """The test -> declaration direction, measured: which enforcers no plant is declared to trip."""
    import testgroups  # noqa: PLC0415

    roster = stages()
    unnamed = sorted(set(roster) - {b for bys in EDGES.values() for b in bys} - {"parse_errors"})
    shard = testgroups.shard_name()
    print(
        f"edges ({shard}): {len(EDGES)} of {cases} cases name the enforcer they trip; "
        f"{len(unnamed)} of {len(roster)} enforcers are named by none"
    )
    from safeedit import _git_path  # noqa: PLC0415

    # LOCAL, never tracked: a derived artefact; `verify --changed` reads it to name a touched enforcer's cases
    # Bounded storage: cap the ledger size to prevent unbounded growth
    payload = json.dumps(EDGES, indent=1, sort_keys=True)
    if len(payload.encode("utf-8")) > MAX_LEDGER_BYTES:
        # Prune to keep only the most recent cases (by insertion order, keep last N)
        max_cases = MAX_LEDGER_BYTES // 100  # rough estimate: 100 bytes per case entry
        pruned = dict(list(EDGES.items())[-max_cases:])
        payload = json.dumps(pruned, indent=1, sort_keys=True)
    _git_path(LEDGER).write_text(payload, encoding="utf-8")
    # A SHARD SEES ONLY ITS OWN CASES, so its unnamed list is not the suite's and judging it would fail a healthy
    # half. CI's edge-coverage job judges the union of the shard ledgers with `--merge` below.
    if shard == "all":
        judge_ceiling(unnamed)


def merge_coverage(paths: list[str]) -> None:
    """CI's edge-coverage job: the union of every shard's ledger, judged against the whole roster."""
    if not paths:
        raise SystemExit("usage: python scripts/edges.py --merge LEDGER.json [LEDGER.json ...]")
    merged: dict[str, list[str]] = {}
    for path in paths:
        merged |= json.loads(Path(path).read_text(encoding="utf-8"))
    roster = stages()
    unnamed = sorted(set(roster) - {b for bys in merged.values() for b in bys} - {"parse_errors"})
    print(
        f"edges (merged {len(paths)} shards): {len(merged)} cases name the enforcer they trip; "
        f"{len(unnamed)} of {len(roster)} enforcers are named by none"
    )
    judge_ceiling(unnamed)


def refusal_cases(module) -> None:
    """A case naming an enforcer that did NOT refuse its plant must fail, on both routes. Test-only."""
    prior = os.environ.get("THEA_CASES_FULL")
    for full in ("", "1"):
        os.environ["THEA_CASES_FULL"] = full
        with module.mutated("VERSION", lambda t: "0.0.1\n"):  # check() refuses it inline; this stage never does
            try:
                module.case(
                    "(planted) an edge to the wrong enforcer", "-", True, "version mismatch", by="inv:schema_first"
                )
            except SystemExit:
                pass
            else:
                raise SystemExit(f"FAIL a case naming an enforcer that never fired passed (THEA_CASES_FULL={full!r})")
        with module.mutated(
            "pyproject.toml",
            lambda t: t.replace('py-modules = ["atlas_cli"]', 'py-modules = ["atlas_cli", "atlas"]', 1),
        ):
            try:  # the first member refuses the plant; the second never does, so the tuple is a false edge
                module.case(
                    "(planted) a tuple edge with one silent member",
                    "-",
                    True,
                    "a harness module in the wheel",
                    by=("declaration_errors", "inv:schema_first"),
                )
            except SystemExit:
                pass
            else:
                raise SystemExit(f"FAIL a case naming an enforcer that never fired passed (THEA_CASES_FULL={full!r})")
    os.environ.pop("THEA_CASES_FULL", None) if prior is None else os.environ.update(THEA_CASES_FULL=prior)
    module.CASES.append(
        (
            "a case naming the wrong enforcer FAILS",
            "a needle printed by a coincidental emitter, so a case stays green after its own enforcer dies",
        )
    )
    print("  ok    a case naming the wrong enforcer FAILS")


def _enforcer_body(name: str):
    """The function a stage name resolves to, for its source span; None for a preflight or a composed lambda."""
    import atlas as module  # noqa: PLC0415

    if name.startswith("inv:"):
        import atlasinv  # noqa: PLC0415

        return atlasinv.INVARIANT_CHECKS[name[4:]]
    owner, _, func = name.rpartition(".")
    if owner:
        module = __import__(owner)
    found = getattr(module, func, None)
    return found if inspect.isfunction(found) else None


def _touched_lines(path: str) -> set[int] | None:
    """Lines the working tree changed in `path`; None = every line (untracked, or no HEAD to diff against)."""
    done = subprocess.run(
        ["git", "diff", "-U0", "HEAD", "--", path],
        cwd=atlas.ROOT,
        capture_output=True,  # noqa: S607
        text=True,
        check=False,
        timeout=60,
    )
    if done.returncode:
        return None
    if not done.stdout:  # an empty diff is NO line for a tracked file, and every line for a new one
        from atlascore import ls_files  # noqa: PLC0415

        return set() if ls_files(atlas.ROOT, path) else None
    lines = set()
    for start, count in re.findall(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", done.stdout, re.M):
        lines.update(range(int(start), int(start) + int(count or 1)))
    return lines


def changed_row(files: list[str], ledger: Path | None = None, touched_lines=None) -> dict:
    """`verify --changed`: every enforcer whose BODY this diff touched, and the planted cases naming it. A
    touched enforcer no case names FAILS, so edge coverage rises where code moves. No ledger is NOT RUN."""
    from safeedit import _git_path  # noqa: PLC0415

    row = {"id": "edges:changed", "argv": ["python", "scripts/atlas_test.py"], "mutates": False}
    ledger = ledger or _git_path(LEDGER)  # a planted case passes its own: the real one is never overwritten
    if not ledger.is_file():
        return row | {"verdict": "NOT RUN", "why": "no edge ledger: run the planted suite once in this clone"}
    counts: dict[str, int] = {}
    for bys in json.loads(ledger.read_text(encoding="utf-8")).values():
        for by in named(bys):  # a ledger from before tuples holds a bare string; named() reads both
            counts[by] = counts.get(by, 0) + 1
    py = {f for f in files if f.endswith(".py")}
    touched = []
    for name in stages():
        body: Any = _enforcer_body(name)
        source = body and Path(cast(str, inspect.getsourcefile(body))).resolve()
        rel = source and source.is_relative_to(atlas.ROOT) and str(source.relative_to(atlas.ROOT))
        if rel not in py:
            continue
        span, first = inspect.getsourcelines(body)
        lines = (touched_lines or _touched_lines)(rel)  # a test passes its own diff, never the worktree's
        if lines is None or lines & set(range(first, first + len(span))):
            touched.append(name)
    bare = [n for n in touched if not counts.get(n)]
    why = f"{len(touched)} touched enforcer(s), {sum(counts.get(n, 0) for n in touched)} planted case(s) name them" + (
        f"; NO case names {bare[:4]} — add a case(by=) before this lands" if bare else ""
    )
    return row | {"verdict": "FAIL" if bare else "PASS", "calls": 1, "why": why[:240]}


if __name__ == "__main__":
    import sys  # noqa: PLC0415

    usage = "usage: python scripts/edges.py --merge LEDGER.json [LEDGER.json ...]"
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(usage)
        raise SystemExit(0)
    if sys.argv[1:2] != ["--merge"]:
        raise SystemExit(usage)
    merge_coverage(sys.argv[2:])
