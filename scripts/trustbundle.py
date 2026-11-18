#!/usr/bin/env python3
"""An Agent Trust Bundle: distribution and verification of authorized agent keys and pinned policy.

WHY. Multi-agent execution and automated pipelines generate changes claiming verified status. An unsigned receipt
or an untrusted agent identity can fabricate proofs. The Agent Trust Bundle packages the authorized agent identities
(SSH allowed signers), their key revocations, and the cryptographic digest of the approved base contract (atlas.yaml).
A reader verifies that an agent was authorized to sign receipts and that execution complied with the pinned policy.

  trust-bundle.json
    bundle_format: "headron-trust-bundle/v1"
    bundle_id: sha256 of canonical fields
    issuer: identity or domain of issuing authority
    issued_at: UTC timestamp (seconds)
    expires_at: UTC timestamp (seconds)
    policy_digest: sha256 of base contract (atlas.yaml)
    allowed_signers: [ "<identity> namespaces=\\"headron-receipt\\" <pubkey>" ]
    revocations: [ "<revoked-fingerprint-or-key>" ]
    signature: optional detached SSH signature over canonical bytes, namespace headron-trust

proves: the bundle is intact, currently valid within its validity window, matches the expected base policy digest,
  holds syntactically valid SSH allowed signers, and if signed, that the trusted authority signed these exact bytes
does_not_prove: that any particular run succeeded, or that individual receipts are genuine; receipts are verified
  separately against the exported allowed signers list using receiptsign.py
closed_by: receiptsign_test.py (trust_bundle_cases), which plants an expired bundle, a future bundle,
  a tampered policy digest, a corrupted allowed signers entry, a revoked signer, a tampered bundle signature,
  and a modified payload
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from receiptsign import sign_detached, verify_detached

BUNDLE_FORMAT = "headron-trust-bundle/v1"
NAMESPACE = "headron-trust"
ALLOWED_SIGNER_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+\s+namespaces=\"[^\"]+\"\s+(?:ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa)\s+[A-Za-z0-9+/=]+.*$"
)
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON bytes over all fields except the detached signature."""
    stripped = {k: v for k, v in payload.items() if k != "signature"}
    return json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _bundle_id(payload: dict[str, Any]) -> str:
    stripped = {k: v for k, v in payload.items() if k not in ("bundle_id", "signature")}
    raw = json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_trust_bundle(
    issuer: str,
    allowed_signers: list[str],
    policy_digest: str,
    *,
    expires_seconds: int = 2592000,
    revocations: list[str] | None = None,
    now: float | None = None,
    signing_key: Path | None = None,
) -> dict[str, Any]:
    """Create a validated Agent Trust Bundle, optionally signing its canonical bytes."""
    current_time = int(time.time() if now is None else now)
    clean_signers = [s.strip() for s in allowed_signers if s.strip()]
    clean_revocations = [r.strip() for r in (revocations or []) if r.strip()]

    if not DIGEST_PATTERN.fullmatch(policy_digest):
        raise ValueError(f"policy_digest must be a 64-char sha256 hex string, got {policy_digest!r}")

    bundle: dict[str, Any] = {
        "bundle_format": BUNDLE_FORMAT,
        "issuer": issuer.strip(),
        "issued_at": current_time,
        "expires_at": current_time + expires_seconds,
        "policy_digest": policy_digest,
        "allowed_signers": clean_signers,
        "revocations": clean_revocations,
    }
    bundle["bundle_id"] = _bundle_id(bundle)

    if signing_key is not None:
        raw_bytes = _canonical_bytes(bundle)
        tmp_sig = signing_key.with_suffix(".bundle.sig")
        try:
            findings = sign_detached(raw_bytes, signing_key, tmp_sig, NAMESPACE)
            if findings:
                raise RuntimeError(f"failed to sign trust bundle: {'; '.join(findings)}")
            bundle["signature"] = tmp_sig.read_bytes().decode("utf-8")
        finally:
            if tmp_sig.exists():
                tmp_sig.unlink()

    return bundle


def verify_trust_bundle(
    bundle_data: dict[str, Any] | bytes | str,
    *,
    expected_policy_digest: str | None = None,
    now: float | None = None,
    signed_by: str | None = None,
    authority_trust: Path | None = None,
    authority_revoked: Path | None = None,
) -> list[str]:
    """Validate trust bundle integrity, timestamp validity, policy alignment, and authority signature.

    Returns empty list when valid, or a list of specific refusal reasons.
    """
    if isinstance(bundle_data, (bytes, str)):
        try:
            bundle = json.loads(bundle_data)
        except Exception as exc:
            return [f"malformed trust bundle JSON: {exc}"]
    elif isinstance(bundle_data, dict):
        bundle = bundle_data
    else:
        return [f"unsupported bundle data type: {type(bundle_data).__name__}"]

    if bundle.get("bundle_format") != BUNDLE_FORMAT:
        return [f"unsupported bundle format: {bundle.get('bundle_format')!r}"]

    expected_id = _bundle_id(bundle)
    if bundle.get("bundle_id") != expected_id:
        return [f"bundle_id mismatch: claimed {bundle.get('bundle_id')!r}, computed {expected_id!r}"]

    current_time = int(time.time() if now is None else now)
    issued_at = bundle.get("issued_at")
    expires_at = bundle.get("expires_at")

    if not isinstance(issued_at, int) or not isinstance(expires_at, int):
        return ["timestamps issued_at and expires_at must be integers"]
    if current_time < issued_at:
        return [f"bundle is not yet valid (issued_at {issued_at} > current {current_time})"]
    if current_time > expires_at:
        return [f"bundle expired at {expires_at} (current {current_time})"]

    policy_digest = bundle.get("policy_digest")
    if not isinstance(policy_digest, str) or not DIGEST_PATTERN.fullmatch(policy_digest):
        return [f"invalid policy_digest format: {policy_digest!r}"]

    if expected_policy_digest is not None and policy_digest != expected_policy_digest:
        return [f"policy_digest mismatch: bundle has {policy_digest!r}, expected {expected_policy_digest!r}"]

    signers = bundle.get("allowed_signers")
    if not isinstance(signers, list):
        return ["allowed_signers must be a list of strings"]
    for idx, signer_line in enumerate(signers):
        if not isinstance(signer_line, str) or not ALLOWED_SIGNER_PATTERN.fullmatch(signer_line.strip()):
            return [f"allowed_signers entry {idx} has invalid SSH allowed signers format: {signer_line!r}"]

    revocations = bundle.get("revocations", [])
    if not isinstance(revocations, list) or not all(isinstance(r, str) for r in revocations):
        return ["revocations must be a list of strings"]

    # If signature verification is requested
    if signed_by is not None:
        sig_text = bundle.get("signature")
        if not sig_text:
            return ["bundle signature missing but verification was requested"]
        if authority_trust is None or not authority_trust.is_file():
            return [f"authority trust list {authority_trust} is missing"]
        raw_bytes = _canonical_bytes(bundle)
        tmp_sig = Path(f"/tmp/headron_bundle_{expected_id[:16]}.sig")
        try:
            tmp_sig.write_text(sig_text, encoding="utf-8")
            sig_findings = verify_detached(raw_bytes, tmp_sig, signed_by, authority_trust, authority_revoked, NAMESPACE)
            if sig_findings:
                return [f"authority signature refused: {'; '.join(sig_findings)}"]
        finally:
            if tmp_sig.exists():
                tmp_sig.unlink()

    return []


def export_trust_files(bundle: dict[str, Any], trust_out: Path, revoked_out: Path | None = None) -> None:
    """Export the bundle's allowed signers and revocation list for receipt verification."""
    signers = bundle.get("allowed_signers", [])
    trust_out.write_text("\n".join(signers) + ("\n" if signers else ""), encoding="utf-8")
    if revoked_out is not None:
        revocations = bundle.get("revocations", [])
        revoked_out.write_text("\n".join(revocations) + ("\n" if revocations else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trustbundle.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    verify_p = sub.add_parser("verify", help="verify an Agent Trust Bundle")
    verify_p.add_argument("bundle", type=Path, help="path to trust-bundle.json")
    verify_p.add_argument("--expected-policy", dest="policy", type=Path, help="path to atlas.yaml to hash")
    verify_p.add_argument("--expected-policy-digest", dest="digest", help="expected 64-char sha256 hash")
    verify_p.add_argument("--signed-by", help="expected authority identity")
    verify_p.add_argument("--trust", type=Path, help="path to authority allowed signers list")
    verify_p.add_argument("--revoked", type=Path, help="path to authority revocation list")

    export_p = sub.add_parser("export", help="export allowed signers and revocations from bundle")
    export_p.add_argument("bundle", type=Path, help="path to trust-bundle.json")
    export_p.add_argument("--trust-out", type=Path, required=True, help="output allowed signers file")
    export_p.add_argument("--revoked-out", type=Path, help="output revocation list file")

    build_p = sub.add_parser("build", help="build an Agent Trust Bundle")
    build_p.add_argument("--issuer", required=True, help="authority identity")
    build_p.add_argument("--allowed-signers-file", type=Path, required=True, help="file containing allowed signers")
    build_p.add_argument("--policy", type=Path, required=True, help="path to atlas.yaml to hash")
    build_p.add_argument("--out", type=Path, required=True, help="output bundle path")
    build_p.add_argument("--key", type=Path, help="signing key for bundle")
    build_p.add_argument("--expires-seconds", type=int, default=2592000, help="bundle validity seconds")

    args = parser.parse_args(argv)

    if args.command == "build":
        if not args.allowed_signers_file.is_file():
            print(f"allowed signers file {args.allowed_signers_file} not found", file=sys.stderr)
            return 1
        if not args.policy.is_file():
            print(f"policy file {args.policy} not found", file=sys.stderr)
            return 1
        signers = [
            line.strip() for line in args.allowed_signers_file.read_bytes().decode("utf-8").splitlines() if line.strip()
        ]
        policy_digest = hashlib.sha256(args.policy.read_bytes()).hexdigest()
        bundle = build_trust_bundle(
            args.issuer, signers, policy_digest, expires_seconds=args.expires_seconds, signing_key=args.key
        )
        args.out.write_bytes(json.dumps(bundle, indent=2).encode("utf-8"))
        print(f"OK: built trust bundle at {args.out}")
        return 0

    if args.command == "verify":
        if not args.bundle.is_file():
            print(f"bundle file {args.bundle} not found", file=sys.stderr)
            return 1
        expected_digest = args.digest
        if expected_digest is None and args.policy is not None:
            if not args.policy.is_file():
                print(f"policy file {args.policy} not found", file=sys.stderr)
                return 1
            expected_digest = hashlib.sha256(args.policy.read_bytes()).hexdigest()

        findings = verify_trust_bundle(
            args.bundle.read_bytes(),
            expected_policy_digest=expected_digest,
            signed_by=args.signed_by,
            authority_trust=args.trust,
            authority_revoked=args.revoked,
        )
        if findings:
            for finding in findings:
                print(f"REFUSED: {finding}", file=sys.stderr)
            return 1
        print("OK: trust bundle verified")
        return 0

    if args.command == "export":
        if not args.bundle.is_file():
            print(f"bundle file {args.bundle} not found", file=sys.stderr)
            return 1
        bundle = json.loads(args.bundle.read_bytes())
        export_trust_files(bundle, args.trust_out, args.revoked_out)
        print(f"OK: exported allowed signers to {args.trust_out}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
