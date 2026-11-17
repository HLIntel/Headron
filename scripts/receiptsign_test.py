"""Planted signing cases: each plants what a signature exists to refuse, the worst being a receipt rewritten with a
recomputed receipt_id, which verify_bytes accepts by design. ron_cases plant the same refusals on a `.ron` bundle
(scripts/ronbundle.py), whose manifest is signed under its own namespace. Loaded by atlas_guards_test.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
ROWS = [{"id": "contract", "verdict": "PASS"}, {"id": "lint", "verdict": "FAIL"}]


def _key(top: Path, name: str) -> Path:
    path = top / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(path)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return path


def _trust_list(top: Path, identity: str, key: Path, *, namespace: str = "headron-receipt") -> Path:
    path = top / f"trust-{key.name}-{namespace}"  # one file per key: a planted wrong signer must not overwrite trust
    path.write_text(f'{identity} namespaces="{namespace}" {key.with_suffix(".pub").read_text()}', encoding="utf-8")
    return path


def _rewrite_to_pass(receipt_module: ModuleType, receipt_file: Path) -> None:
    """The forgery verify_bytes cannot see: the verdict turned to PASS with every derived field recomputed."""
    rows = [{"id": "contract", "verdict": "PASS"}, {"id": "lint", "verdict": "PASS"}]
    forged = receipt_module.build(rows, base_commit="a" * 40, policy_digest="b" * 64, input_digest="c" * 64)
    receipt_file.write_text(receipt_module.dumps(forged), encoding="utf-8")


def run(module: ModuleType) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import receipt as receipt_module  # noqa: PLC0415
    import receiptsign  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        top = Path(tmp)
        signer, other = _key(top, "signer"), _key(top, "other")
        trusted = _trust_list(top, "signer@example.test", signer)
        built = receipt_module.build(ROWS, base_commit="a" * 40, policy_digest="b" * 64, input_digest="c" * 64)
        original = receipt_module.dumps(built)
        receipt_file = top / "receipt.json"
        receipt_file.write_text(original, encoding="utf-8")

        unsigned = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted)
        signed = receiptsign.sign(receipt_file, signer)
        genuine = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted)
        bytes_kept = receipt_file.read_text(encoding="utf-8") == original
        wrong_identity = receiptsign.verify_signed(receipt_file, "someone@example.test", trusted)
        empty_identity = receiptsign.verify_signed(receipt_file, "", trusted)
        other_signer = receiptsign.verify_signed(
            receipt_file, "signer@example.test", _trust_list(top, "signer@example.test", other)
        )
        other_namespace = receiptsign.verify_signed(
            receipt_file, "signer@example.test", _trust_list(top, "signer@example.test", signer, namespace="git")
        )

        revoked_list, other_list = top / "revoked.krl", top / "other.krl"
        for krl, key in ((revoked_list, signer), (other_list, other)):
            subprocess.run(
                ["ssh-keygen", "-q", "-k", "-f", str(krl), str(key.with_suffix(".pub"))],
                check=True,
                capture_output=True,
                timeout=30,
            )
        on_the_list = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted, revoked_list)
        not_on_the_list = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted, other_list)
        list_gone = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted, top / "no-such.krl")

        def cli(*argv: str) -> int:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return receipt_module.main(list(argv))

        path, who = str(receipt_file), "signer@example.test"
        cli_genuine = cli("verify", path, "--signed-by", who, "--trust", str(trusted))
        cli_revoked = cli("verify", path, "--signed-by", who, "--trust", str(trusted), "--revoked", str(revoked_list))
        cli_half = cli("verify", path, "--signed-by", who)
        cli_revoked_alone = cli("verify", path, "--revoked", str(revoked_list))

        _rewrite_to_pass(receipt_module, receipt_file)
        hash_still_fine = not receipt_module.verify_bytes(receipt_file.read_bytes())
        forged_verdict = json.loads(receipt_file.read_text(encoding="utf-8"))["verdict"]
        forged = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted)
        receipt_file.write_text(original, encoding="utf-8")

        broken = top / "broken.json"
        broken.write_text(original.replace('"verdict"', '"verdict_"'), encoding="utf-8")
        refuses_broken = receiptsign.sign(broken, signer)
        no_broken_signature = not receiptsign.signature_path(broken).exists()
        # A key can sign anything, so a valid signature over bytes that fail their own check must still refuse.
        subprocess.run(
            ["ssh-keygen", "-q", "-Y", "sign", "-f", str(signer), "-n", "headron-receipt", str(broken)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        signed_but_broken = receiptsign.verify_signed(broken, "signer@example.test", trusted)

        saved_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(top / "no-such-bin")
        try:
            no_tool = receiptsign.verify_signed(receipt_file, "signer@example.test", trusted)
        finally:
            os.environ["PATH"] = saved_path

        cases = [
            (
                "a receipt rewritten with a recomputed receipt_id passes the hash check and is refused by its signature",
                "a forged PASS that recomputes receipt_id, which integrity alone accepts",
                hash_still_fine and forged_verdict == "PASS" and bool(forged),
                (hash_still_fine, forged_verdict, forged),
            ),
            (
                "the listed key's signature verifies, and signing leaves the receipt's bytes as they were",
                "a signer that rewrites the receipt it signs, or a checker that refuses everything",
                not signed and not genuine and bytes_kept,
                (signed, genuine, bytes_kept),
            ),
            (
                "another key, another identity or no identity is refused",
                "a checker that accepts any valid signature rather than this identity's",
                bool(other_signer and wrong_identity and empty_identity),
                (other_signer, wrong_identity, empty_identity),
            ),
            (
                "a key allowed only for another namespace is refused, so a signature made for git does not count",
                "a signature made for one purpose accepted for another",
                bool(other_namespace),
                other_namespace,
            ),
            (
                "an unsigned receipt, a receipt that fails its own check and a missing tool are refusals, never passes",
                "a missing signature or a missing ssh-keygen read as verified, or a broken receipt signed or accepted",
                bool(unsigned and refuses_broken and no_tool and signed_but_broken) and no_broken_signature,
                (unsigned, refuses_broken, no_tool, signed_but_broken, no_broken_signature),
            ),
            (
                "a revoked key is refused, another key's revocation does not touch this one, and a named list that is missing refuses",
                "a revocation list that is ignored, that refuses everyone, or that passes when it cannot be read",
                bool(on_the_list) and "revocation list" in " ".join(list_gone) and not not_on_the_list,
                (on_the_list, not_on_the_list, list_gone),
            ),
            (
                "the command line checks the signer it was asked about, and half a signer check is a usage error, not a plain verify",
                "--signed-by or --revoked without the trust list quietly falling back to the integrity check alone",
                (cli_genuine, cli_revoked, cli_half, cli_revoked_alone) == (0, 1, 2, 2),
                (cli_genuine, cli_revoked, cli_half, cli_revoked_alone),
            ),
        ]
    for name, kills, ok, got in cases:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  got: {got!r}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")
    ron_cases(module)
    ron_evidence_cases(module)


def _redigest(bundle: Path, edit: object = None) -> None:
    """Recompute every digest and the bundle_id after an edit: the forgery integrity alone cannot see."""
    import ronbundle  # noqa: PLC0415

    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    files = {rel: ronbundle._sha((bundle / rel).read_bytes()) for rel in manifest["files"] if (bundle / rel).is_file()}
    body = {**{k: v for k, v in manifest.items() if k != "bundle_id"}, "files": files}
    if callable(edit):
        edit(body)
    (bundle / "manifest.json").write_bytes(ronbundle._dump({**body, "bundle_id": ronbundle.digest(body)}))


def ron_cases(module: ModuleType) -> None:
    """A `.ron` bundle verifies only as packed, refuses anything added, removed, linked or edited, keeps standing
    apart from integrity, and its signature neither forges nor stands in for a receipt's."""
    import obligations  # noqa: PLC0415
    import receipt as receipt_module  # noqa: PLC0415
    import ronbundle  # noqa: PLC0415

    def verify_says(bundle: Path) -> str:
        findings, contract = ronbundle.verify(bundle)
        return "intact" if not findings and contract else " | ".join(findings)

    def cli(*argv: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return ronbundle.main(list(argv))

    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"HEADRON_HOME": tmp}):
        top = Path(tmp)
        signer, other = _key(top, "signer"), _key(top, "other")
        ron_trust = _trust_list(top, "signer@example.test", signer, namespace="headron-ron")
        wrong_trust = _trust_list(top, "signer@example.test", other, namespace="headron-ron")
        receipt_trust = _trust_list(top, "signer@example.test", signer)
        receipt_file = top / "run.json"
        receipt_file.write_text(
            receipt_module.dumps(
                receipt_module.build(ROWS[:1], base_commit="a" * 40, policy_digest="b" * 64, input_digest="c" * 64)
            ),
            encoding="utf-8",
        )
        log = top / "pytest.log"
        log.write_text("12 passed\n", encoding="utf-8")
        obligations.add("lane-r", "tests", "the suite passes", "pytest")
        obligations.close("lane-r", "tests", "receipts/run.json", at="t1")
        obligations.add("lane-open", "docs", "the docs say so", "headron check")
        good = top / "good.ron"
        packed = ronbundle.pack("lane-r", good, [receipt_file], [log], key=signer, at="t1")
        intact = verify_says(good)
        signed = ronbundle.verify_detached
        sig_ok = signed(
            (good / "manifest.json").read_bytes(),
            good / ronbundle.SIGNATURE,
            "signer@example.test",
            ron_trust,
            None,
            ronbundle.NAMESPACE,
        )
        sig_as_receipt = signed(
            (good / "manifest.json").read_bytes(),
            good / ronbundle.SIGNATURE,
            "signer@example.test",
            receipt_trust,
            None,
            "headron-receipt",
        )

        def planted(name: str, plant: object) -> str:
            bundle = top / f"{name}.ron"
            shutil.copytree(good, bundle, symlinks=True)
            if callable(plant):
                plant(bundle)
            return verify_says(bundle)

        def tampered_receipt(bundle: Path) -> None:
            data = json.loads((bundle / "receipts/run.json").read_text(encoding="utf-8"))
            data["verdict"] = "FAIL"  # the good receipt passes; claiming FAIL breaks its own counts
            (bundle / "receipts/run.json").write_text(json.dumps(data), encoding="utf-8")
            _redigest(bundle)

        def forged_log(bundle: Path) -> None:
            (bundle / "evidence/pytest.log").write_text("0 failed\n", encoding="utf-8")
            _redigest(bundle)

        found = {
            "edited": planted("edited", lambda b: (b / "evidence/pytest.log").write_text("x", encoding="utf-8")),
            "unlisted": planted("unlisted", lambda b: (b / "evidence/extra").write_text("x", encoding="utf-8")),
            "missing": planted("missing", lambda b: (b / "evidence/pytest.log").unlink()),
            "symlink": planted("symlink", lambda b: (b / "evidence/link").symlink_to(log)),
            "dotdot": planted("dotdot", lambda b: _redigest(b, lambda m: m["files"].update({"../x": "0" * 64}))),
            "wrong hash": planted(
                "wronghash", lambda b: _redigest(b, lambda m: m["files"].update({"contract.json": "0" * 64}))
            ),
            "renamed task": planted(
                "renamed",
                lambda b: (b / "manifest.json").write_text(
                    (b / "manifest.json").read_text(encoding="utf-8").replace('"lane-r"', '"lane-x"'), encoding="utf-8"
                ),
            ),
            "receipt": planted("receipt", tampered_receipt),
        }
        forged = top / "forged.ron"
        shutil.copytree(good, forged)
        forged_log(forged)
        forged_sig = signed(
            (forged / "manifest.json").read_bytes(),
            forged / ronbundle.SIGNATURE,
            "signer@example.test",
            ron_trust,
            None,
            ronbundle.NAMESPACE,
        )
        forged_says = verify_says(forged)
        wrong_signer = signed(
            (good / "manifest.json").read_bytes(),
            good / ronbundle.SIGNATURE,
            "signer@example.test",
            wrong_trust,
            None,
            ronbundle.NAMESPACE,
        )
        rows = json.loads((good / "contract.json").read_text(encoding="utf-8"))["obligations"]
        trees = ("t1", "t2", "t1+dirty", ronbundle.UNKNOWN_TREE)
        agree = (
            ronbundle.STATES == obligations.STATES
            and ronbundle.UNKNOWN_TREE == obligations.UNKNOWN_TREE
            and all(
                (ronbundle.standing([row], now)[1] == "") == (obligations.standing(row, now) == "proven")
                for row in [*rows, {**rows[0], "state": "unknown"}, *({**rows[0], "tree": tree} for tree in trees)]
                for now in trees
            )
        )
        refusals = [
            ronbundle.pack("lane-r", good, [receipt_file], [], at="t1"),  # exists
            ronbundle.pack("lane-r", top / "plain", [receipt_file], [], at="t1"),  # not .ron
            ronbundle.pack("lane-none", top / "none.ron", [], [], at="t1"),  # nothing owed
            ronbundle.pack("lane-r", top / "bad.ron", [log], [], at="t1"),  # not a receipt
            ronbundle.pack("lane-r", top / "dup.ron", [receipt_file, receipt_file], [], at="t1"),  # same name twice
        ]
        open_bundle = top / "open.ron"
        ronbundle.pack("lane-open", open_bundle, [], [], at="t1")
        here = Path.cwd()
        os.chdir(top)  # outside any git tree: --tree reads unknown-tree, which no evidence covers
        try:
            exits = (
                cli("verify", str(good)),
                cli("verify", str(good), "--signed-by", "signer@example.test", "--trust", str(ron_trust)),
                cli("verify", str(good), "--signed-by", "signer@example.test", "--trust", str(receipt_trust)),
                cli("verify", str(top / "edited.ron")),
                cli("verify", str(open_bundle)),
                cli("verify", str(good), "--tree"),
            )
        finally:
            os.chdir(here)
    expect = {
        "edited": "does not match",
        "unlisted": "not in manifest",
        "missing": "listed but missing",
        "symlink": "symlink",
        "dotdot": "plain relative path",
        "wrong hash": "does not match",
        "renamed task": "bundle_id does not recompute",
        "receipt": "receipts/run.json",
    }
    cases = [
        (
            "a packed .ron bundle verifies intact and its manifest signature checks under the headron-ron namespace",
            "a bundle that refuses its own fresh bytes, or a signature that never verifies",
            packed == [] and intact == "intact" and sig_ok == [],
            (packed, intact, sig_ok),
        ),
        (
            "a .ron bundle refuses an edited, unlisted, missing or linked file, a .. path, a wrong digest, an edited "
            "manifest and a tampered receipt, each by name",
            "a verifier that checks only the files the manifest lists, or trusts a re-digested receipt",
            all(expect[k] in found[k] for k in expect),
            found,
        ),
        (
            "a .ron signature refuses a re-digested forgery and a wrong signer, and never verifies as a receipt signature",
            "a namespace shared with receipts, a trust list that is not consulted, or integrity taken as authorship",
            forged_says == "intact" and bool(forged_sig) and bool(wrong_signer) and bool(sig_as_receipt),
            (forged_says, forged_sig, wrong_signer, sig_as_receipt),
        ),
        (
            "ronbundle.standing agrees with obligations.standing, and pack refuses an existing path, a non-.ron path, "
            "a task with nothing owed, a receipt that does not verify and two files of one name",
            "a bundle rule for proven that drifts from the ledger's, or a pack that writes over or around a refusal",
            agree and all(refusals) and not any((top / name).exists() for name in ("none.ron", "bad.ron", "dup.ron")),
            (agree, refusals),
        ),
        (
            "ronbundle verify exits 0 intact and proven, 1 on a finding or a wrong-namespace signer, 3 when an obligation "
            "is open or the current tree is not the one its evidence covers",
            "an intact bundle read as a finished task, or a stale tree read as proven",
            exits == (0, 0, 1, 1, 3, 3),
            exits,
        ),
    ]
    for name, kills, ok, got in cases:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  got: {got!r}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")


def ron_evidence_cases(module: ModuleType) -> None:
    """A proven obligation stands in a `.ron` only on evidence the bundle holds: a ref to nothing in it, or to a
    receipt that answers FAIL, leaves the obligation open (verify exits 3 and says why); a ref by last segment holds."""
    import obligations  # noqa: PLC0415
    import receipt as receipt_module  # noqa: PLC0415
    import ronbundle  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"HEADRON_HOME": tmp}):
        top = Path(tmp)
        receipts = {}
        for name, rows in (("run.json", ROWS[:1]), ("fail.json", ROWS)):
            receipts[name] = top / name
            built = receipt_module.build(rows, base_commit="a" * 40, policy_digest="b" * 64, input_digest="c" * 64)
            receipts[name].write_text(receipt_module.dumps(built), encoding="utf-8")
        bound = {  # task: (evidence ref the close names, receipt packed), and the exit verify owes
            "lane-failed": ("receipts/fail.json", "fail.json", 3),
            "lane-elsewhere": ("the CI log on the runner", "run.json", 3),
            "lane-basename": (str(receipts["run.json"]), "run.json", 0),
            "lane-path": ("receipts/run.json", "run.json", 0),
        }
        exits, why = {}, {}
        for task, (ref, packed, _) in bound.items():
            obligations.add(task, "tests", "the suite passes", "pytest")
            obligations.close(task, "tests", ref, at="t1")
            bundle = top / f"{task}.ron"
            ronbundle.pack(task, bundle, [receipts[packed]], [], at="t1")
            rows = json.loads((bundle / "contract.json").read_text(encoding="utf-8"))["obligations"]
            why[task] = ronbundle.evidence_problems(bundle, rows).get("tests", "")
            with contextlib.redirect_stdout(io.StringIO()):
                exits[task] = ronbundle.main(["verify", str(bundle)])
    ok = (
        exits == {task: want for task, (_, _, want) in bound.items()}
        and "answers FAIL" in why["lane-failed"]
        and "not in the bundle" in why["lane-elsewhere"]
        and why["lane-basename"] == why["lane-path"] == ""
    )
    name = (
        "a proven obligation stands in a .ron only when its evidence ref names a bundle file, by path or last "
        "segment, and a receipt it names answers PASS; else verify exits 3 and names why"
    )
    kills = "a ledger evidence string never resolved to the bundle, or a FAIL receipt taken as the proof"
    if not ok:
        raise SystemExit(f"FAIL {name}\n  got: {(exits, why)!r}\n  kills: {kills}")
    module.CASES.append((name, kills))
    print(f"  ok    {name}")
