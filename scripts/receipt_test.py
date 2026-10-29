"""Planted receipt cases (receipt v1): a verdict that is a verdict, a policy read from base, and a receipt that
verifies from its own bytes. Loaded by atlas_guards_test; each case plants the defect a verdict could hide:
a NOT RUN read as a pass, a SKIP read as a pass, a missing input read as a skip, a policy edited in the PR head,
a receipt whose bytes disagree with its verdict, and a verdict that moves between two runs of one tree.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS_ROWS = [{"id": "contract", "verdict": "PASS"}, {"id": "lint", "verdict": "PASS"}]
BASE_ATLAS = (
    "verification_policy:\n  done_set:\n  - {id: contract, argv: [python, scripts/atlas.py, check], mutates: false}\n"
)
EDITED_ATLAS = "verification_policy:\n  done_set: []\n"


def _build(receipt, rows, policy_digest: str | None = "b" * 64):
    return receipt.build(rows, base_commit="a" * 40, policy_digest=policy_digest, input_digest="c" * 64)


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return done.stdout.strip()


def _policy_repo(top: Path, head_atlas: str | None) -> str:
    """A base commit with BASE_ATLAS, then a PR commit whose atlas.yaml is head_atlas (None removes it)."""
    _git(top, "init", "-q", "-b", "main")
    (top / "atlas.yaml").write_text(BASE_ATLAS)
    _git(top, "add", "atlas.yaml")
    _git(top, "commit", "-qm", "base")
    base = _git(top, "rev-parse", "HEAD")
    if head_atlas is None:
        _git(top, "rm", "-q", "atlas.yaml")
    else:
        (top / "atlas.yaml").write_text(head_atlas)
    _git(top, "commit", "-qam", "pr", "--allow-empty")
    return base


def _without_repo_access(receipt_file: Path) -> subprocess.CompletedProcess:
    """The verifier run isolated: isolated mode, a cwd outside any repository, and no PYTHONPATH."""
    with tempfile.TemporaryDirectory(prefix="headron-receipt-cwd-") as outside:
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "GIT_DIR", "GIT_WORK_TREE")}
        return subprocess.run(
            [sys.executable, "-I", str(ROOT / "scripts" / "receipt.py"), "verify", str(receipt_file)],
            cwd=outside,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )


def run(module) -> None:
    try:
        import jsonschema  # noqa: PLC0415
    except ImportError:  # a missing validator is a finding: the schema cases cannot run, so the suite fails
        raise SystemExit(
            "FAIL receipt_test: jsonschema is not installed, so tools/receipt.schema.json was not checked"
        ) from None

    import receipt  # noqa: PLC0415
    import verify  # noqa: PLC0415

    schema = json.loads((ROOT / "tools" / "receipt.schema.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="headron-receipt-") as tmp:
        top = Path(tmp)
        edited_repo = top / "edited"
        edited_repo.mkdir()
        edited_base = _policy_repo(edited_repo, EDITED_ATLAS)
        same_repo = top / "same"
        same_repo.mkdir()
        same_base = _policy_repo(same_repo, BASE_ATLAS)
        removed_repo = top / "removed"
        removed_repo.mkdir()
        removed_base = _policy_repo(removed_repo, None)
        nogit = top / "nogit"
        nogit.mkdir()
        (nogit / "atlas.yaml").write_text(BASE_ATLAS)
        edited = verify.policy_pin(edited_repo, ["--base", edited_base])
        same = verify.policy_pin(same_repo, ["--base", same_base])
        removed = verify.policy_pin(removed_repo, ["--base", removed_base])
        no_base = verify.policy_pin(nogit, [])
        receipt_file = top / "receipt.json"
        receipt_file.write_text(json.dumps(_build(receipt, PASS_ROWS), indent=2) + "\n", encoding="utf-8")
        intact = _without_repo_access(receipt_file)
        tampered = top / "tampered.json"
        tampered.write_text(receipt_file.read_text().replace('"verdict": "PASS"', '"verdict": "FAIL"', 1))
        tamper = _without_repo_access(tampered)
        first = _build(
            receipt, [{"id": "contract", "verdict": "PASS", "seconds": 1.2}, {"id": "lint", "verdict": "PASS"}]
        )
        second = _build(
            receipt,
            [
                {"id": "contract", "verdict": "REUSED", "seconds": 0, "why": "REUSED evidence"},
                {"id": "lint", "verdict": "PASS"},
            ],
        )
        skip_only = _build(receipt, [{"id": "x", "verdict": "SKIP"}])
        mixed = _build(receipt, [*PASS_ROWS, {"id": "y", "verdict": "SKIP"}])
        unknown = _build(receipt, [{"id": "x", "verdict": "PASSED"}, {"id": "y"}])
        no_policy_pass = _build(receipt, PASS_ROWS, policy_digest=None)
        bad_state = json.loads(json.dumps(_build(receipt, PASS_ROWS)))
        bad_state["checks"][0]["state"] = "PASSED"
        verdicts = [
            _build(receipt, [{"id": "x", "verdict": "PASS"}, {"id": "y", "verdict": "NOT RUN", "why": "gone"}]),
            _build(receipt, [{"id": "x", "verdict": "NOT RUN"}]),
            _build(receipt, []),
        ]
        schema_ok = True
        try:
            jsonschema.validate(_build(receipt, PASS_ROWS), schema)
            jsonschema.validate(_build(receipt, [*PASS_ROWS, {"id": "y", "verdict": "SKIP"}]), schema)
            jsonschema.validate(_build(receipt, [{"id": "x", "verdict": "NOT RUN"}]), schema)
        except jsonschema.ValidationError:
            schema_ok = False

        def _refused(candidate) -> bool:
            try:
                jsonschema.validate(candidate, schema)
            except jsonschema.ValidationError:
                return True
            return False

        schema_refuses = _refused(bad_state) and _refused(no_policy_pass)
        numeric_receipt = _build(receipt, PASS_ROWS)
        numeric_receipt["schema"] = 1.0
        numeric_receipt["counts"]["PASS"] = 2.0
        numeric_receipt["receipt_id"] = receipt.digest({k: v for k, v in numeric_receipt.items() if k != "receipt_id"})
        malformed = []
        for field, value in (
            ("base_commit", "bad"),
            ("input_digest", "bad"),
            ("policy", {"source": "base", "digest": "bad"}),
            ("counts", {"PASS": True, "FAIL": 0, "NOT RUN": 0, "SKIP": 0}),
            ("checks", [{"id": "", "state": "PASS"}]),
            ("extra", 1),
        ):
            candidate = _build(receipt, PASS_ROWS)
            candidate[field] = value
            candidate["receipt_id"] = receipt.digest({k: v for k, v in candidate.items() if k != "receipt_id"})
            malformed.append(candidate)
        cases = [
            (
                "a NOT RUN check, alone or beside PASSes, never yields PASS; an empty receipt is NOT RUN",
                "a gate that did not run counted as a pass because the others passed, or no check at all counted as done",
                [v["verdict"] for v in verdicts] == ["NOT RUN", "NOT RUN", "NOT RUN"],
                [v["verdict"] for v in verdicts],
            ),
            (
                "a SKIP is counted apart and never a pass: skip-only is NOT RUN, and beside a PASS it is not counted as one",
                "a skipped gate tallied into PASS so a receipt of nothing but skips reads as proof",
                skip_only["verdict"] == "NOT RUN"
                and skip_only["counts"]["SKIP"] == 1
                and skip_only["counts"]["PASS"] == 0
                and mixed["counts"] == {"PASS": 2, "FAIL": 0, "NOT RUN": 0, "SKIP": 1}
                and mixed["verdict"] == "PASS",
                (skip_only["verdict"], skip_only["counts"], mixed["counts"], mixed["verdict"]),
            ),
            (
                "a verdict the receipt does not recognise, or a row with none, is a FAIL finding, never a skip or a pass",
                "a row whose verdict was lost on the way into the receipt, recorded as a skip so the run stays green",
                [c["state"] for c in unknown["checks"]] == ["FAIL", "FAIL"] and unknown["verdict"] == "FAIL",
                [c["state"] for c in unknown["checks"]],
            ),
            (
                "a policy edited in the PR head is refused: FAIL, read from the base commit, the digest is the base's",
                "a PR that drops its own gates from verification_policy and then reports a green receipt",
                edited["row"]["verdict"] == "FAIL"
                and "edited" in edited["row"]["why"]
                and edited["base_commit"] == edited_base,
                (edited["row"], edited["base_commit"] == edited_base),
            ),
            (
                "a policy unchanged from base passes its pin; the pin names the base commit and its digest",
                "a pin that refuses every receipt, so a clean repository could never prove anything",
                same["row"]["verdict"] == "PASS"
                and same["base_commit"] == same_base
                and len(same["digest"] or "") == 64,
                same["row"],
            ),
            (
                "a policy removed in the PR head is refused, not read as an empty policy",
                "a PR that deletes atlas.yaml so the pin has nothing to compare and reads silence as a match",
                removed["row"]["verdict"] == "FAIL" and removed["base_commit"] == removed_base,
                removed["row"],
            ),
            (
                "a missing input is a FAIL finding: no base commit, and no atlas.yaml at base, are never a skip",
                "a repository without a base or a policy turning absence of evidence into a green receipt",
                no_base["row"]["verdict"] == "FAIL" and no_base["digest"] is None and no_base["base_commit"] is None,
                no_base["row"],
            ),
            (
                "a receipt verifies from its own bytes with no repository access: an intact one passes, a tampered verdict is refused",
                "a verifier that re-derives the verdict from the repo it was run in, so the receipt proves only its author's tree",
                intact.returncode == 0 and tamper.returncode == 1,
                (intact.returncode, intact.stdout, tamper.returncode, tamper.stdout, tamper.stderr),
            ),
            (
                "a PASS verdict without a pinned policy digest is refused by the verifier",
                "a hand-written receipt that says PASS over no policy, which the schema alone cannot tell apart",
                any("policy" in f for f in receipt.verify_bytes(json.dumps(no_policy_pass).encode())),
                receipt.verify_bytes(json.dumps(no_policy_pass).encode()),
            ),
            (
                "two runs of one tree give byte-identical receipts: re-use and timing do not move the verdict",
                "a receipt that records seconds or REUSED-versus-PASS, so the same tree is judged two ways",
                json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True),
                (first["verdict"], second["verdict"]),
            ),
            (
                "tools/receipt.schema.json accepts real receipts and refuses a check state outside PASS/FAIL/NOT RUN/SKIP",
                "a schema that describes the shape of a receipt but lets an invented state through",
                schema_ok
                and schema_refuses
                and not _refused(numeric_receipt)
                and not receipt.verify_bytes(json.dumps(numeric_receipt).encode())
                and bool(receipt.verify_bytes(("[" * 2000 + "]" * 2000).encode()))
                and all(_refused(item) and receipt.verify_bytes(json.dumps(item).encode()) for item in malformed),
                (schema_ok, schema_refuses),
            ),
        ]
    for name, kills, ok, got in cases:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  got: {got!r}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")
