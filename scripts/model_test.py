#!/usr/bin/env python3
"""Regression cases for `thea model` and the student rung of `thea judge`, each guard with a mutant that must die.

The fixture (scripts/fixtures/model/) is a real bundle the private model repo's own loader wrote, its judgments.yaml,
and golden.json: that loader's answers and `thea model --json` record for it at the commit modelpack.py names. The
drift guard runs the vendored loader against golden.json, so a re-vendor that moves an answer fails here, in CI.
A mutant is the guarded source with one check removed, run through the same scenario: the scenario must pass on the
real source and FAIL on the mutant, or the check it names guards nothing.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import shutil
import tempfile
import types
from pathlib import Path
from typing import Any, cast

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "model"
IDS = ("needs_confirmation", "work_kind")
DASH_RUNGS = ("rules", "teacher", "student")


def _jtext(edited: bool = False, comment: bool = False) -> str:
    """The fixture judgments.yaml; edited changes needs_confirmation's own record (its contract), comment adds only a
    comment line, which stales no pack."""
    text = (FIXTURE / "judgments.yaml").read_text(encoding="utf-8")
    if edited:
        text = text.replace("  act_at: 0.9\n", "  act_at: 0.95\n", 1)
    return text + "\n# edited\n" if comment else text


def _attach(root: Path, name: str = "b1") -> Path:
    """A target whose `current` points at a fresh copy of the fixture bundle, as the private attach lays it out."""
    target = root / name
    (target / "bundles").mkdir(parents=True)
    shutil.copytree(FIXTURE / "bundle", target / "bundles" / name)
    (target / "current").symlink_to(f"bundles/{name}")
    return target


def _tamper(target: Path) -> None:
    """One bias nudged: still valid JSON and a valid pack, so only the sha256 can catch it."""
    f = target / "current" / "work_kind.json"
    pack = json.loads(f.read_text(encoding="utf-8"))
    pack["head"]["b"][1] += 0.001
    f.write_text(json.dumps(pack, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def _mutant(module: types.ModuleType, old: str, new: str) -> types.ModuleType:
    """`module` with one guard rewritten, loaded fresh under its own name."""
    src = Path(cast(str, module.__file__)).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise SystemExit(f"FAIL mutation site in {module.__name__} is not unique: {old!r}")
    mod = types.ModuleType(module.__name__)
    mod.__file__ = module.__file__
    exec(compile(src.replace(old, new), f"{module.__name__}_mutant.py", "exec"), mod.__dict__)  # noqa: S102
    return mod


def _run(fn, *args) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = fn(*args)
    return rc, out.getvalue()


def theaos_rows(record: dict, local_sha: str) -> dict[str, str]:
    """The verdict TheaOS's Model page gives each row of a schema 1 record: the same rules its parser
    applies (vendored as rules, not code), so a record shape it would not READ fails here before it ships."""
    if record.get("schema") != 1 or record.get("command") != "model" or not isinstance(record.get("judgments"), dict):
        return {"_record": "not the frozen schema 1 shape"}
    if record.get("judgments_sha") != local_sha:
        return {"_record": "thea read another judgments.yaml"}
    rows = {}
    for jid, j in record["judgments"].items():
        held = j.get("heldout")
        nums = held if isinstance(held, dict) else {}
        ok_held = all(
            isinstance(nums.get(k), (int, float)) and not isinstance(nums.get(k), bool)
            for k in ("score", "rows", "bar")
        )
        if not {"rung", "key", "pack_sha", "heldout"} <= set(j) or j["rung"] not in DASH_RUNGS:
            rows[jid] = "NOT RUN"
        elif j["rung"] == "student" and (not j["pack_sha"] or not ok_held):
            rows[jid] = "NOT RUN"
        else:
            rows[jid] = "STALE" if j["rung"] == "student" and j["pack_sha"] != local_sha else "READ"
    return rows


def golden_case(module) -> None:
    """The drift guard: the vendored loader answers what the source commit's loader answered, within tolerance."""
    import modelpack

    golden = json.loads((FIXTURE / "golden.json").read_text(encoding="utf-8"))
    tol = float(golden["tolerance"])
    drift = []
    with tempfile.TemporaryDirectory() as tmp:
        target = _attach(Path(tmp))
        for case in golden["cases"]:
            got = modelpack.decide(target, case["state"], list(IDS), _jtext())
            for jid, want in case["answers"].items():
                have = got[jid]
                if have.get("answer") != want["answer"] or not math.isclose(have["p"], want["p"], abs_tol=tol):
                    drift.append(f"{jid} on {case['state'][:24]!r}: {have.get('answer')} {have.get('p')} != {want}")
                drift += [
                    f"{jid} on {case['state'][:24]!r}: dist[{a}] {have['dist'].get(a)} != {v}"
                    for a, v in want["dist"].items()
                    if not math.isclose(have["dist"].get(a, -1.0), v, abs_tol=tol)
                ]
        record = modelpack.model_record(modelpack.status(target, _jtext()))
    if record != golden["model_record"]:
        drift.append(f"model record {record} != golden {golden['model_record']}")
    if drift or not golden["cases"]:
        raise SystemExit("FAIL the vendored loader drifted from golden.json:\n  " + "\n  ".join(drift[:8] or ["empty"]))
    module.CASES.append(
        (
            f"the vendored student loader matches the source commit's answers on {len(golden['cases'])} golden states",
            "a re-vendored loader that answers differently from the model it claims to run",
        )
    )
    print(f"  ok    modelpack: {len(golden['cases'])} golden states and the model record match within {tol}")


def record_case(module) -> None:
    """`thea model --json` is the schema 1 record TheaOS reads; the exit code follows the verdict."""
    import model
    import modelpack

    jschema = json.loads((Path(__file__).resolve().parent.parent / "tools" / "atlas-output.schema.json").read_text())
    saved = model.judgments_text
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target = _attach(Path(tmp))
            model.judgments_text = _jtext
            rc, out = _run(model.main, ["--json", "--to", str(target)])
            record = json.loads(out)
            rows = theaos_rows(record, modelpack.sha256_text(_jtext()))
            assert rc == 0 and rows == dict.fromkeys(IDS, "READ"), f"fresh fixture: rc={rc} rows={rows}"
            try:
                import jsonschema  # noqa: PLC0415  (optional: the rules above run without it)

                jsonschema.validate(record, {"$ref": "#/$defs/model", "$defs": jschema["$defs"]})
            except ImportError:
                pass
            model.judgments_text = lambda: _jtext(comment=True)
            rc, out = _run(model.main, ["--json", "--to", str(target)])
            rows = theaos_rows(json.loads(out), modelpack.sha256_text(_jtext(comment=True)))
            assert rc == 0 and rows == dict.fromkeys(IDS, "READ"), f"a comment edit staled a pack: rc={rc} rows={rows}"
            model.judgments_text = lambda: _jtext(edited=True)
            rc, out = _run(model.main, ["--to", str(target)])
            assert rc == 1 and "STATUS NOT RUN" in out and "NOT RUN needs_confirmation" in out, f"stale: rc={rc}\n{out}"
            rc, out = _run(model.main, ["--json", "--to", str(target)])
            rows = theaos_rows(json.loads(out), modelpack.sha256_text(_jtext(edited=True)))
            assert rows == {"needs_confirmation": "STALE", "work_kind": "READ"}, f"one edited judgment: rows={rows}"
            rc, out = _run(model.main, ["--json", "--to", str(Path(tmp) / "none")])
            assert rc == 1 and json.loads(out)["judgments"] == {}, f"no bundle: rc={rc} {out}"
    finally:
        model.judgments_text = saved
    module.CASES.append(
        (
            "thea model --json is TheaOS's schema 1 record; one edited judgment is STALE alone, a comment none",
            "a record the Model page cannot read, or a NOT RUN that exits 0",
        )
    )
    print("  ok    thea model: schema 1 record READ by TheaOS's rules; comment edit OK; stale and missing exit 1")


def sha_mutant_case(module) -> None:
    """A tampered pack is NOT RUN; with the sha256 check removed it answers."""
    import modelpack

    def held(mod) -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            target = _attach(Path(tmp))
            _tamper(target)
            got = mod.decide(target, "it pushes to a shared remote", list(IDS), _jtext())
            return all(got[j].get("verdict") == "NOT RUN" for j in IDS)

    weak = _mutant(modelpack, 'if got != p["sha256"]:', "if False:")
    assert held(modelpack), "a tampered bundle answered on the real loader"
    assert not held(weak), "MUTANT SURVIVED: removing the sha256 check changed nothing"
    module.CASES.append(("a pack whose sha256 is not its manifest's is NOT RUN", "a tampered pack that answers"))
    print("  ok    modelpack: a tampered pack is NOT RUN; the mutant without the sha check answers")


def stale_mutant_case(module) -> None:
    """A pack whose judgment's record changed is NOT RUN, in status and in decide; each check, removed, answers."""
    import model
    import modelpack

    def status_held(mod) -> bool:
        saved = (model.modelpack, model.judgments_text)
        model.modelpack, model.judgments_text = mod, (lambda: _jtext(edited=True))
        try:
            with tempfile.TemporaryDirectory() as tmp:
                return _run(model.main, ["--to", str(_attach(Path(tmp)))])[0] == 1
        finally:
            model.modelpack, model.judgments_text = saved

    def pack_held(mod) -> bool:
        got = mod.student_decide(FIXTURE / "bundle", "it pushes", ["needs_confirmation"], _jtext(edited=True))
        return got["needs_confirmation"].get("verdict") == "NOT RUN"

    status_weak = _mutant(modelpack, 'if now != e["contract_sha"]:', "if False:")
    pack_weak = _mutant(modelpack, 'if pack.get("contract_sha") != contract:', "if False:")
    assert status_held(modelpack) and pack_held(modelpack), "a stale bundle answered on the real loader"
    assert not status_held(status_weak), "MUTANT SURVIVED: the bundle staleness check guards nothing"
    assert not pack_held(pack_weak), "MUTANT SURVIVED: the pack staleness check guards nothing"
    module.CASES.append(
        (
            "a pack trained on another contract than its judgment's record is NOT RUN",
            "a student answering a contract it was never trained on",
        )
    )
    print(
        "  ok    modelpack: a changed contract is NOT RUN in status and in decide; each mutant without its check answers"
    )


def fallback_mutant_case(module) -> None:
    """judge: the student answers with its calibrated p when its pack verifies; otherwise the caller's answer on the
    declared rung, named on the line. Mutants: no fallback, and a teacher-rung judgment answered by the student."""
    import judge
    import model

    spec = judge.records()["needs_confirmation"]
    saved = model.judgments_text
    model.judgments_text = _jtext
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target, stale = str(_attach(Path(tmp))), str(_attach(Path(tmp), "b2"))
            _tamper(Path(stale))
            want = model.student("needs_confirmation", "it pushes to a shared remote", target)
            rc, out = _run(
                judge.student_rung, "needs_confirmation", spec, None, None, "it pushes to a shared remote", target
            )
            assert want["p"] < 1 and f"p={want['p']:g}" in out and "rung student" in out and rc == 0, (rc, out, want)
            rc, out = _run(judge.student_rung, "needs_confirmation", spec, "no", "0.95", "x", stale)
            assert rc == 0 and "rung rules (student NOT RUN" in out, (rc, out)
            rc, out = _run(judge.student_rung, "needs_confirmation", spec, None, None, "x", stale)
            assert rc == 2 and "refused" in out, (rc, out)

            def falls_back(mod) -> bool:
                code, line = _run(mod.student_rung, "needs_confirmation", spec, "no", "0.95", "x", stale)
                return code == 0 and "rung rules" in line

            def rung_held(mod) -> bool:
                return mod.student("work_kind", "where does the config live", target).get("rung") == "teacher"

            no_fallback = _mutant(
                judge,
                '    if answer is None or p is None:\n        print(f"refused: {name} student',
                '    if True:\n        print(f"refused: {name} student',
            )
            any_rung: Any = _mutant(model, 'if entry["rung"] != "student":', "if False:")
            assert falls_back(judge) and rung_held(model), (
                "the real judge did not fall back, or answered a teacher rung"
            )
            assert not falls_back(no_fallback), "MUTANT SURVIVED: removing the fallback changed nothing"
            any_rung.judgments_text = _jtext
            assert not rung_held(any_rung), (
                "MUTANT SURVIVED: the student answered a judgment the manifest puts on teacher"
            )
    finally:
        model.judgments_text = saved
    module.CASES.append(
        (
            "judge: the student answers with its calibrated p when its pack verifies, else the caller on the named rung",
            "a student answer on a bad pack, or a judge that refuses when the old rung could answer",
        )
    )
    print("  ok    judge --state: student p kept, fallback names its rung; both mutants die")


def home_case(module) -> None:
    """With no bundle attached in the cwd, `thea model` reads THEA_HOME/model: thea's own home, never a companion
    app's folder. The mutant points the fallback back at an app's Application Support folder and must escape it."""
    import os

    import model

    def under_home(mod) -> bool:
        saved_home, saved_cwd = os.environ.get("THEA_HOME"), Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["THEA_HOME"] = tmp
            os.chdir(tmp)
            try:
                return mod.target_dir(None) == mod.target_dir("home") == Path(tmp) / "model"
            finally:
                os.chdir(saved_cwd)
                if saved_home is None:
                    os.environ.pop("THEA_HOME", None)
                else:
                    os.environ["THEA_HOME"] = saved_home

    assert under_home(model), "FAIL thea model's fallback bundle is not THEA_HOME/model"
    app_folder = 'Path.home() / "Library" / "Application Support" / "TheaOS" / "model"'
    assert not under_home(_mutant(model, 'return thea_home() / "model"', f"return {app_folder}")), (
        "MUTANT SURVIVED: a fallback in an app's folder passed as thea's home"
    )
    module.CASES.append(
        (
            "model: the fallback bundle is THEA_HOME/model, and --to home names the same folder",
            "a bundle path inside a companion app's folder, which moves when the app is renamed",
        )
    )
    print("  ok    thea model: fallback and --to home are THEA_HOME/model; app-folder mutant dies")


def run(module) -> None:
    golden_case(module)
    record_case(module)
    sha_mutant_case(module)
    stale_mutant_case(module)
    fallback_mutant_case(module)
    home_case(module)


if __name__ == "__main__":
    run(types.SimpleNamespace(CASES=[]))
    print("model tests: pass")
