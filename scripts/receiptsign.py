#!/usr/bin/env python3
"""Who wrote a receipt: a detached SSH signature over its exact bytes.

WHY. receipt_id detects an edited receipt, and whoever edits one can recompute it. A signature ties the bytes to
a key the reader already trusts, so the rewritten receipt that verify_bytes accepts is refused here. The receipt's
bytes and schema do not change, and an unsigned receipt still verifies as before.

NO NEW DEPENDENCY. ssh-keygen signs and checks, and the private key can stay on a hardware token. Headron never holds
a key. Trust and revocation stay with the reader: its trust list and its revocation list, never a file the signer's
repo ships. A trust list holds one `<identity> namespaces="headron-receipt" <public key>` per line.

proves: the key listed for this identity, and not on the reader's revocation list, signed exactly these bytes, under Headron's receipt namespace
does_not_prove: that the checks ran as the receipt says; a signer can sign a false receipt, so this names who to ask
closed_by: receiptsign_test.py, which plants a rewritten receipt, a wrong signer, a wrong namespace, a revoked key and a missing tool
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from receipt import verify_bytes

# A signature for one purpose must not verify for another, so it is bound to this name.
NAMESPACE = "headron-receipt"
# A hardware key waits for a touch.
TIMEOUT_SECONDS = 120


def signature_path(receipt: Path) -> Path:
    return receipt.with_name(receipt.name + ".sig")


def _ssh_keygen(args: list[str], data: bytes) -> tuple[bytes | None, str]:
    """Stdout on success, or None and the reason. A tool that cannot run is a refusal, never a pass."""
    try:
        done = subprocess.run(
            ["ssh-keygen", "-Y", *args, "-n", NAMESPACE],
            input=data,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"ssh-keygen did not run: {exc}"
    if done.returncode:
        reason = (done.stderr or done.stdout).decode(errors="replace").strip().splitlines()
        return None, reason[0] if reason else f"ssh-keygen exited {done.returncode}"
    return done.stdout, ""


def sign(receipt: Path, key: Path) -> list[str]:
    """Write <receipt>.sig. A receipt that does not verify is not signed."""
    data = receipt.read_bytes()
    findings = verify_bytes(data)
    if findings:
        return findings
    signature, reason = _ssh_keygen(["sign", "-f", str(key)], data)
    if signature is None:
        return [f"not signed: {reason}"]
    signature_path(receipt).write_bytes(signature)
    return []


def verify_signed(receipt: Path, signed_by: str, trust: Path, revoked: Path | None = None) -> list[str]:
    """Findings, empty only when the receipt is intact and this identity's listed, unrevoked key signed these bytes.

    revoked names an ssh-keygen revocation list. A named list that is missing is a refusal: a reader who asked for
    the revocation check must not get a pass without it.
    """
    data = receipt.read_bytes()
    findings = verify_bytes(data)
    if findings:
        return findings
    signature = signature_path(receipt)
    if not signature.is_file():
        return [f"{signature.name} is missing, so this receipt is unsigned"]
    if not trust.is_file():
        return [f"trust list {trust} is missing"]
    if revoked is not None and not revoked.is_file():
        return [f"revocation list {revoked} is missing"]
    args = ["verify", "-f", str(trust), "-I", signed_by, "-s", str(signature)]
    if revoked is not None:
        args += ["-r", str(revoked)]
    _, reason = _ssh_keygen(args, data)
    return [f"signature refused for {signed_by!r}: {reason}"] if reason else []
