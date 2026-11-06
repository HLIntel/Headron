"""Planted signing cases: each plants what a signature exists to refuse, the worst being a receipt rewritten with a
recomputed receipt_id, which verify_bytes accepts by design. Loaded by atlas_guards_test.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

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
