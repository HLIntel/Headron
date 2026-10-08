#!/usr/bin/env python3
"""Regression cases for `thea judge`: the exit code is the verdict, and calibration scores the bar."""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path


def runner_pin_case(module) -> None:
    """A workflow on a `-latest` runner is refused by immutable_first; the pinned tree is not (control)."""
    import atlasinv

    if atlasinv._inv_immutable_first():
        raise SystemExit(f"FAIL immutable_first fires on the pinned tree: {atlasinv._inv_immutable_first()}")
    with module.mutated(
        ".github/workflows/polyglot.yml", lambda s: s.replace("runs-on: macos-15", "runs-on: macos-latest", 1)
    ):
        planted = atlasinv._inv_immutable_first()
    if "moving image" not in str(planted):
        raise SystemExit(f"FAIL a macos-latest runner was not refused: {planted}")
    module.CASES.append(("a CI job on a -latest runner is refused", "an image that moves under a green build"))
    print("  ok    immutable_first: a -latest runner is refused, the pinned tree passes")


def run(module) -> None:
    runner_pin_case(module)
    """The exit code IS the verdict, calibration catches a bar the outcomes do not support, and a record
    with an undeclared answer or a coin-flip bar is refused by the contract."""
    import judge

    judged = [
        (
            "    one_line: the answer is a verdict",
            "    one_liner: the answer is a verdict",
            "a judgment giving a meaning to an answer it does not offer is refused",
            "'one_line' has no declared",
        ),
        (
            "  act_at: 0.9\n",
            "  act_at: 0.5\n",
            "a judgment whose bar a coin flip clears is refused",
            "a guess clears it",
        ),
        (
            "{no_gate: frontier}",
            "{no_gate: genius}",
            "a judgment whose fact forces an answer it does not offer is refused",
            "genius",
        ),
        (
            "  below: escalate\n",
            "  below: default:maybe\n",
            "a judgment defaulting to an answer it does not offer is refused",
            "default:maybe",
        ),
        (
            "  prevents: a_local_green_read_as_a_verdict",
            "  prevents: a_failure_nobody_recorded",
            "a judgment preventing a failure the ledger does not hold is refused",
            "a_failure_nobody_recorded",
        ),
        ("  kind: yes_no\n", "  kind: noul\n", "a judgment of a retired kind is refused", "kind 'noul' is not one of"),
    ]
    for current, planted, name, needle in judged:
        with module.mutated("systems/judgments.yaml", lambda s, c=current, p=planted: s.replace(c, p, 1)):
            module.case(
                name,
                "a decision code acts on with no declared meaning or bar",
                expect_fail=True,
                needle=needle,
                by="inv:autonomous_profile_is_enforced",
            )

    quiet = contextlib.redirect_stdout(io.StringIO())
    with quiet:
        codes = [
            judge.main(argv)
            for argv in (
                ["needs_confirmation", "no", "0.95"],
                ["needs_confirmation", "no", "0.7"],
                ["needs_confirmation", "no", "0.95", "--fact", "irreversible"],
                ["needs_confirmation", "--fact", "irreversibel"],
                ["work_kind", "edit", "1.5"],
            )
        ]
    assert codes == [0, 3, 0, 2, 2], f"act, below, fact overrides p, misspelt fact refused, bad p refused: {codes}"
    module.CASES.append(
        (
            "judge: act at the bar, take `below` under it, a fact beats p, a misspelt fact is refused",
            "a verdict that ignores an undeclared fact, so a hard rule silently never fires",
        )
    )
    print("  ok    judge: act, below, fact over p, misspelt fact and bad p refused")
    with tempfile.TemporaryDirectory() as tmp:
        rows = Path(tmp) / "outcomes.tsv"
        # acted at p 0.9 but right only 6 times in 10: the bar 0.9 does not hold; the top band at 0.99 does.
        rows.write_text(
            "".join(f"needs_confirmation\tno\t0.9\t{'pass' if i < 18 else 'fail'}\n" for i in range(30))
            + "".join("needs_confirmation\tno\t0.99\tpass\n" for _ in range(20)),
            encoding="utf-8",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = judge.calibrate(str(rows))
        assert rc == 1 and "raise act_at to 0.99" in out.getvalue(), out.getvalue()
        rows.write_text("needs_confirmation\tno\t0.95\tpass\n" * 5, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert judge.calibrate(str(rows)) == 0 and "unmeasured" in out.getvalue(), (
                "five rows are unmeasured, never a held bar"
            )
        # 22 clean rows clear a 0.9 bar on the point but their lower bound is 0.85: held, NOT PROVEN, --strict fails it.
        rows.write_text("needs_confirmation\tno\t0.95\tpass\n" * 22, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert judge.calibrate(str(rows)) == 0 and "NOT PROVEN" in out.getvalue(), out.getvalue()
        with contextlib.redirect_stdout(io.StringIO()):
            assert judge.calibrate(str(rows), strict=True) == 1, "--strict must fail a bar proven only on the point"
        rows.write_text("needs_confirmation\tno\t0.95\tpass\n" * 40, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert judge.calibrate(str(rows), strict=True) == 0 and "PROVEN" in out.getvalue(), out.getvalue()
    assert judge.wilson_lower(20, 20) < 0.84 and judge.clean_run(0.9) == 35, "the Wilson bound and the clean-run size"
    module.CASES.append(
        (
            "judge --calibrate fails a bar the outcomes do not support and names the bar that holds",
            "a confidence bar argued from taste and never scored against what happened",
        )
    )
    print("  ok    judge --calibrate: a low bar fails and names the bar that holds; five rows are unmeasured")
