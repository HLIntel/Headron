#!/usr/bin/env python3
"""Headron receipt v1: one verify run as a record that verifies from its own bytes.

WHY (receipt v1). A verify run's verdict lived in the terminal and in a marker inside .git, which nothing
outside this clone could read or re-check. A receipt is the same verdict as data: the base commit the policy
was read from, the tree the checks ran over, each check's state, and the verdict those states give. This is
the ONE mapping from states to a verdict and the ONE checker of a receipt. It is stdlib only, so a receipt is
verified from its bytes with no repository at hand.

STATES. PASS, FAIL, NOT RUN, SKIP. A verdict is PASS only with at least one PASS and no FAIL and no NOT RUN;
SKIP is counted apart and is never a pass. A verdict this module does not recognise is a FAIL finding.
INTEGRITY, NOT AUTHENTICITY. receipt_id detects an edited receipt; it does not prove who wrote it. Signing is
unresolved and out of scope here.

  python scripts/receipt.py verify <file>     exit 0 when intact; 1 with each finding printed
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RECEIPT_SCHEMA = 1
KIND = "headron.receipt"
STATES = ("PASS", "FAIL", "NOT RUN", "SKIP")
REQUIRED = ("receipt_id", "base_commit", "policy", "input_digest", "checks", "counts", "verdict")
FINDING_WHY_CAP = 200


def check_state(verdict: object) -> str:
    """A verify row's verdict as a receipt state. REUSED is a PASS for this tree; anything unrecognised is a FAIL."""
    if verdict in ("PASS", "REUSED"):
        return "PASS"
    return verdict if verdict in STATES else "FAIL"


def verdict_of(states: list[str]) -> str:
    """FAIL on any FAIL; NOT RUN on any NOT RUN or on no PASS at all (SKIPs alone, or no checks); else PASS."""
    if "FAIL" in states:
        return "FAIL"
    if "NOT RUN" in states or "PASS" not in states:
        return "NOT RUN"
    return "PASS"


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def build(rows: list[dict], *, base_commit: str | None, policy_digest: str | None, input_digest: str) -> dict:
    """One receipt from verify rows. A PASS row's why is dropped, so a re-used proof and a fresh one write the same bytes."""
    checks = []
    for row in rows:
        state = check_state(row.get("verdict"))
        check = {"id": str(row.get("id", "")), "state": state}
        if state != "PASS":
            check["why"] = str(row.get("why") or f"verdict {row.get('verdict')!r}")[:FINDING_WHY_CAP]
        checks.append(check)
    states = [check["state"] for check in checks]
    body = {
        "schema": RECEIPT_SCHEMA,
        "kind": KIND,
        "base_commit": base_commit,
        "policy": {"source": "base", "digest": policy_digest},
        "input_digest": input_digest,
        "checks": checks,
        "counts": {state: states.count(state) for state in STATES},
        "verdict": verdict_of(states),
    }
    return {"receipt_id": digest(body), **body}


def dumps(receipt: dict) -> str:
    return json.dumps(receipt, indent=2) + "\n"


def verify_bytes(data: bytes) -> list[str]:
    """Each finding against a receipt's own bytes; an empty list means intact. Reads no repository."""
    try:
        receipt = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        return [f"not a JSON receipt: {error}"]
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("kind") != KIND:
        return [f"not a {KIND} schema {RECEIPT_SCHEMA} record"]
    missing = [field for field in REQUIRED if field not in receipt]
    if missing:
        return [f"missing field(s): {', '.join(missing)}"]
    checks = receipt["checks"]
    if not isinstance(checks, list) or any(not isinstance(c, dict) or c.get("state") not in STATES for c in checks):
        return ["a check state is outside PASS, FAIL, NOT RUN, SKIP"]
    states = [check["state"] for check in checks]
    findings = []
    body = {key: value for key, value in receipt.items() if key != "receipt_id"}
    if receipt["receipt_id"] != digest(body):
        findings.append("receipt_id does not match the receipt's contents: edited or mis-copied")
    if receipt["counts"] != {state: states.count(state) for state in STATES}:
        findings.append("counts disagree with the checks")
    if receipt["verdict"] != verdict_of(states):
        findings.append(f"verdict {receipt['verdict']!r} is not what the checks give ({verdict_of(states)!r})")
    policy = receipt["policy"] if isinstance(receipt["policy"], dict) else {}
    if receipt["verdict"] == "PASS" and not policy.get("digest"):
        findings.append("PASS without a pinned policy digest: nothing says which policy it was judged against")
    return findings


USAGE = "usage: receipt.py verify <file>   (-h/--help prints this)"


def main(argv: list[str]) -> int:
    if argv in (["-h"], ["--help"]):
        print(USAGE)
        return 0
    if len(argv) != 2 or argv[0] != "verify":
        print(USAGE, file=sys.stderr)
        return 2
    data = Path(argv[1]).read_bytes()
    findings = verify_bytes(data)
    if findings:
        for finding in findings:
            print(f"FAIL  {finding}")
        return 1
    receipt = json.loads(data)
    print(f"ok    {receipt['receipt_id']}  verdict {receipt['verdict']}  {len(receipt['checks'])} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
