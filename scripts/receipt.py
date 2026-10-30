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

import contextlib
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA = 1
KIND = "headron.receipt"
STATES = ("PASS", "FAIL", "NOT RUN", "SKIP")
REQUIRED = ("receipt_id", "base_commit", "policy", "input_digest", "checks", "counts", "verdict")
FINDING_WHY_CAP = 200


def _shape_error(receipt: dict) -> str | None:
    """Check the v1 schema with the standard library, including nested fields."""

    def sha(value: object, length: int) -> bool:
        return isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is not None

    if set(receipt) != {*REQUIRED, "schema", "kind"}:
        return "receipt fields do not match schema 1"
    if isinstance(receipt["schema"], bool) or receipt["schema"] != 1 or receipt["kind"] != KIND:
        return "receipt schema or kind is invalid"
    if not sha(receipt["receipt_id"], 64) or not sha(receipt["input_digest"], 64):
        return "receipt_id or input_digest is not a sha256 digest"
    base = receipt["base_commit"]
    if base is not None and not sha(base, 40):
        return "base_commit is not a commit hash or null"
    policy = receipt["policy"]
    if not isinstance(policy, dict) or set(policy) != {"source", "digest"} or policy["source"] != "base":
        return "policy fields or source are invalid"
    if policy["digest"] is not None and not sha(policy["digest"], 64):
        return "policy digest is not a sha256 digest or null"
    checks = receipt["checks"]
    if not isinstance(checks, list):
        return "checks is not an array"
    for check in checks:
        if not isinstance(check, dict) or not {"id", "state"} <= set(check) <= {"id", "state", "why"}:
            return "check fields are invalid"
        if not isinstance(check["id"], str) or not check["id"] or check["state"] not in STATES:
            return "check id or state is invalid"
        if "why" in check and not isinstance(check["why"], str):
            return "check why is not a string"
    counts = receipt["counts"]
    if not isinstance(counts, dict) or set(counts) != set(STATES):
        return "counts fields are invalid"
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()))
        or value < 0
        for value in counts.values()
    ):
        return "counts must be nonnegative integers"
    if receipt["verdict"] not in STATES:
        return "verdict is invalid"
    return None


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
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        return [f"not a JSON receipt: {error}"]
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("kind") != KIND:
        return [f"not a {KIND} schema {RECEIPT_SCHEMA} record"]
    missing = [field for field in REQUIRED if field not in receipt]
    if missing:
        return [f"missing field(s): {', '.join(missing)}"]
    shape_error = _shape_error(receipt)
    if shape_error:
        return [shape_error]
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


@dataclass(frozen=True)
class ReceiptSummary:
    """Summary of an execution receipt verified against receipt v1 integrity rules."""

    receipt_id: str
    verdict: str
    base_commit: str
    policy_digest: str
    checks_count: int
    pass_count: int
    fail_count: int
    valid: bool
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "verdict": self.verdict,
            "base_commit": self.base_commit,
            "policy_digest": self.policy_digest,
            "checks_count": self.checks_count,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "valid": self.valid,
            "timestamp": self.timestamp,
        }


def _receipt_entry(rid: str, verdict: str, base: str, dig: str, chk: int, p_cnt: int, f_cnt: int, valid: bool) -> dict:
    return ReceiptSummary(rid, verdict, base, dig, chk, p_cnt, f_cnt, valid, time.time()).to_dict()


def record_receipt(receipt_data: dict | str | Any) -> dict:
    """Validate and record an execution receipt into persistent telemetry.

    proves: receipt verifies against receipt v1 integrity rules before storage
    does_not_prove: that underlying checks were executed correctly
    closed_by: mind_test.py, which verifies recording and tampering detection
    """
    from safeedit import _git_path  # noqa: PLC0415

    if isinstance(receipt_data, (str, Path)):
        p = Path(receipt_data)
        if not p.is_file():
            raise ValueError(f"no such receipt file: {receipt_data}")
        raw = p.read_bytes()
        body = json.loads(raw.decode("utf-8"))
    else:
        body = receipt_data
        raw = canonical(body)

    valid = len(verify_bytes(raw)) == 0
    cnt = body.get("counts") or {}
    pol = body.get("policy") or {}
    p_dig = pol.get("digest", "") if isinstance(pol, dict) else ""
    summary = _receipt_entry(
        str(body.get("receipt_id", "")),
        str(body.get("verdict", "UNKNOWN")),
        str(body.get("base_commit", "")),
        str(p_dig),
        len(body.get("checks", [])),
        int(cnt.get("PASS", 0)),
        int(cnt.get("FAIL", 0)),
        valid,
    )
    with contextlib.suppress(OSError):
        with open(_git_path("headron-receipts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")
    return summary


def _load_jsonl_receipts(seen: set[str], records: list[dict]) -> None:
    from safeedit import _git_path  # noqa: PLC0415

    with contextlib.suppress(OSError, json.JSONDecodeError):
        store = _git_path("headron-receipts.jsonl")
        if store.is_file():
            for line in store.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    if (rid := entry.get("receipt_id")) and rid not in seen:
                        records.append(entry)
                        seen.add(rid)


def _load_last_verify_receipt(seen: set[str], records: list[dict]) -> None:
    from safeedit import _git_path  # noqa: PLC0415

    with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
        last_v = _git_path("headron-last-verify.json")
        if last_v.is_file():
            d = json.loads(last_v.read_text(encoding="utf-8"))
            if rows := d.get("rows", []):
                # NO PLACEHOLDER DIGESTS: a field the run did not record stays empty, so the entry reads invalid.
                built = build(
                    rows,
                    base_commit=d.get("base"),
                    policy_digest=d.get("policy_digest"),
                    input_digest=d.get("input_digest") or "",
                )
                if (rid := built["receipt_id"]) not in seen:
                    cnt, pol = built.get("counts") or {}, built.get("policy") or {}
                    valid = len(verify_bytes(canonical(built))) == 0
                    records.append(
                        _receipt_entry(
                            rid,
                            built["verdict"],
                            built["base_commit"],
                            pol.get("digest", ""),
                            len(built.get("checks", [])),
                            int(cnt.get("PASS", 0)),
                            int(cnt.get("FAIL", 0)),
                            valid,
                        )
                    )
                    seen.add(rid)


def _load_dir_receipts(directory: Path, limit: int, seen: set[str], records: list[dict]) -> None:
    for f in sorted(directory.glob("*.json")) + sorted(directory.glob("*.receipt")):
        if len(records) >= limit:
            break
        with contextlib.suppress(OSError, json.JSONDecodeError):
            raw = f.read_bytes()
            findings, b = verify_bytes(raw), json.loads(raw.decode("utf-8"))
            if (rid := b.get("receipt_id")) and rid not in seen:
                cnt, pol = b.get("counts") or {}, b.get("policy") or {}
                p_dig = pol.get("digest", "") if isinstance(pol, dict) else ""
                records.append(
                    _receipt_entry(
                        rid,
                        b.get("verdict", "UNKNOWN"),
                        b.get("base_commit", ""),
                        p_dig,
                        len(b.get("checks", [])),
                        int(cnt.get("PASS", 0)),
                        int(cnt.get("FAIL", 0)),
                        len(findings) == 0,
                    )
                )
                seen.add(rid)


def gather_receipts(directory: Any = None, limit: int = 20) -> list[dict]:
    """Gather and verify execution receipts across runs."""
    records: list[dict] = []
    seen: set[str] = set()
    _load_jsonl_receipts(seen, records)
    _load_last_verify_receipt(seen, records)
    if directory and (dp := Path(directory)).is_dir():
        _load_dir_receipts(dp, limit, seen, records)
    return records[:limit]


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
