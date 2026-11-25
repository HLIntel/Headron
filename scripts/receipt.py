#!/usr/bin/env python3
"""Headron receipt v1: one verify run as a record that verifies from its own bytes.

WHY (receipt v1). A verify run's verdict lived in the terminal and in a marker inside .git, which nothing
outside this clone could read or re-check. A receipt is the same verdict as data: the base commit the policy
was read from, the tree the checks ran over, each check's state, and the verdict those states give. This is
the ONE mapping from states to a verdict and the ONE checker of a receipt. It is stdlib only, so a receipt is
verified from its bytes with no repository at hand.

STATES. PASS, FAIL, NOT RUN, SKIP. A verdict is PASS only with at least one PASS and no FAIL, NOT RUN, or SKIP;
SKIP is counted apart and makes the verdict incomplete. A verdict this module does not recognise is a FAIL finding.
INTEGRITY, NOT AUTHENTICITY. receipt_id detects an edited receipt; it does not prove who wrote it. The optional
detached signature in receiptsign.py does that, and leaves these bytes and this check as they are.

  headron receipt verify <file>     exit 0 when intact; 1 with each finding printed
  headron receipt sign <file> --key <private key>     write <file>.sig
  headron receipt verify <file> --signed-by <identity> --trust <file> [--revoked <file>]
                                    also check who signed, and that the key is not revoked
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, NotRequired, TypedDict

RECEIPT_SCHEMA = 1
KIND = "headron.receipt"
COMPUTATION_KIND = "headron.computation_receipt"
STATES = ("PASS", "FAIL", "NOT RUN", "SKIP")
COMPUTATION_STATUSES = ("ok", "unknown", "refused", "error")


def _is_sha_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is not None


class Policy(TypedDict):
    source: str
    digest: str | None


class Check(TypedDict):
    id: str
    state: str
    why: NotRequired[str]


class ReceiptBody(TypedDict):
    """What is hashed into `receipt_id`: tools/receipt.schema.json, as a type."""

    schema: int
    kind: str
    base_commit: str | None
    policy: Policy
    input_digest: str
    checks: list[Check]
    counts: dict[str, int]
    verdict: str


class Receipt(ReceiptBody):
    receipt_id: str


REQUIRED = ("receipt_id", "base_commit", "policy", "input_digest", "checks", "counts", "verdict")
FINDING_WHY_CAP = 200


def _shape_error(receipt: dict) -> str | None:
    """Check the v1 schema with the standard library, including nested fields."""
    if set(receipt) != {*REQUIRED, "schema", "kind"}:
        return "receipt fields do not match schema 1"
    if isinstance(receipt["schema"], bool) or receipt["schema"] != 1 or receipt["kind"] != KIND:
        return "receipt schema or kind is invalid"
    if not _is_sha_hex(receipt["receipt_id"], 64) or not _is_sha_hex(receipt["input_digest"], 64):
        return "receipt_id or input_digest is not a sha256 digest"
    base = receipt["base_commit"]
    # Spelled here, not imported: this file verifies alone. gitobject_test holds the two to one answer.
    if base is not None and not (_is_sha_hex(base, 40) or _is_sha_hex(base, 64)):
        return "base_commit is not a commit hash or null"
    policy = receipt["policy"]
    if not isinstance(policy, dict) or set(policy) != {"source", "digest"} or policy["source"] != "base":
        return "policy fields or source are invalid"
    if policy["digest"] is not None and not _is_sha_hex(policy["digest"], 64):
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
    """FAIL on any FAIL; NOT RUN on any NOT RUN or SKIP, or on no checks; else PASS."""
    if any(state not in STATES or state == "FAIL" for state in states):
        return "FAIL"
    if "NOT RUN" in states or "SKIP" in states or "PASS" not in states:
        return "NOT RUN"
    return "PASS"


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def as_check(row: Mapping[str, Any]) -> Check:
    """Any result row (`state` or `verdict`, `id`, optional `why`) as a receipt check. A PASS drops its why, so a
    re-used proof and a fresh one write the same bytes; a non-PASS always says why."""
    raw = row.get("state", row.get("verdict"))
    check: Check = {"id": str(row.get("id", "")), "state": check_state(raw)}
    if check["state"] != "PASS":
        check["why"] = str(row.get("why") or f"verdict {raw!r}")[:FINDING_WHY_CAP]
    return check


def build(rows: list[dict], *, base_commit: str | None, policy_digest: str | None, input_digest: str) -> Receipt:
    """One receipt from verify rows."""
    checks = [as_check(row) for row in rows]
    states = [check["state"] for check in checks]
    body: ReceiptBody = {
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


def build_computation_receipt(
    *,
    program: str,
    version: str,
    inputs: Any,
    outputs: Any,
    status: str,
    checks: Iterable[Mapping[str, Any]] = (),
    evidence_refs: Iterable[str] = (),
) -> dict:
    """The one computation-receipt producer. Callers pass the rows they already have (`as_check` shape); the
    verdict is derived here, never hand-mapped. No rows: the status is the one check. Raises when status and
    verdict disagree (ok iff PASS), so a contradictory receipt is never written."""
    rows = [as_check(row) for row in checks] or [
        as_check({"id": f"{program}.status", "state": "PASS" if status == "ok" else "FAIL", "why": f"status {status}"})
    ]
    verdict = verdict_of([row["state"] for row in rows])
    if (status == "ok") != (verdict == "PASS"):
        raise ValueError(f"{program}: status {status!r} contradicts check verdict {verdict}")
    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "kind": COMPUTATION_KIND,
        "program": str(program),
        "version": str(version),
        "status": str(status),
        "input_digest": digest(inputs),
        "output_digest": digest(outputs) if outputs is not None else None,
        "verification": {"verdict": verdict, "checks": rows},
        "evidence_refs": [str(r) for r in evidence_refs],
    }
    return {"receipt_id": digest(body), **body}


def dumps(receipt: Mapping[str, object]) -> str:
    return json.dumps(receipt, indent=2) + "\n"


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


COMPUTATION_REQUIRED = (
    "schema",
    "kind",
    "receipt_id",
    "program",
    "version",
    "status",
    "input_digest",
    "output_digest",
    "verification",
    "evidence_refs",
)


def _computation_shape_error(receipt: dict) -> str | None:
    if set(receipt) != set(COMPUTATION_REQUIRED):
        return "computation receipt fields do not match schema 1"
    if isinstance(receipt["schema"], bool) or receipt["schema"] != 1 or receipt["kind"] != COMPUTATION_KIND:
        return "computation receipt schema or kind is invalid"
    if not _is_sha_hex(receipt["receipt_id"], 64) or not _is_sha_hex(receipt["input_digest"], 64):
        return "receipt_id or input_digest is not a sha256 digest"
    if receipt["output_digest"] is not None and not _is_sha_hex(receipt["output_digest"], 64):
        return "output_digest must be a sha256 digest or null"
    if not isinstance(receipt["program"], str) or not receipt["program"].strip():
        return "program is not a non-empty string"
    if not isinstance(receipt["version"], str) or not receipt["version"].strip():
        return "version is not a non-empty string"
    if receipt["status"] not in COMPUTATION_STATUSES:
        return f"status is outside {list(COMPUTATION_STATUSES)}"
    if receipt["status"] == "ok" and receipt["output_digest"] is None:
        return "status is ok but output_digest is null"
    if not isinstance(receipt["verification"], dict):
        return "verification must be an object"
    if not isinstance(receipt["evidence_refs"], list) or any(not isinstance(r, str) for r in receipt["evidence_refs"]):
        return "evidence_refs must be a list of strings"
    return None


def verify_computation_receipt(receipt: dict) -> list[str]:
    """Check a computation receipt against its integrity rules."""
    shape_err = _computation_shape_error(receipt)
    if shape_err:
        return [shape_err]
    findings = []
    body = {k: v for k, v in receipt.items() if k != "receipt_id"}
    if receipt["receipt_id"] != digest(body):
        findings.append("receipt_id does not match the computation's contents: edited or mis-copied")
    return findings


def verify_bytes(data: bytes) -> list[str]:
    """Each finding against a receipt's own bytes; an empty list means intact. Reads no repository."""
    try:
        receipt = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        return [f"not a JSON receipt: {error}"]
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]
    if receipt.get("kind") == COMPUTATION_KIND:
        return verify_computation_receipt(receipt)
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("kind") != KIND:
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
    if receipt["verdict"] == "PASS" and not receipt["base_commit"]:
        findings.append("PASS without a base commit: nothing identifies where the policy was pinned")
    return findings


@dataclass(frozen=True)
class ReceiptSummary:
    """Summary of an execution receipt verified against receipt v1 integrity rules."""

    receipt_id: str
    verdict: str
    base_commit: str | None
    policy_digest: str | None
    checks_count: int
    pass_count: int
    fail_count: int
    valid: bool
    timestamp: float

    def to_dict(self) -> dict:
        return asdict(self)


def _marker_path() -> Path:
    """The last verify's marker, resolved lazily so a plain verify never loads safeedit."""
    from safeedit import _git_path  # noqa: PLC0415

    return _git_path("headron-last-verify.json")


def _load_last_verify_receipt(seen: set[str], records: list[dict]) -> None:
    with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
        last_v = _marker_path()
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
                        ReceiptSummary(
                            rid,
                            built["verdict"],
                            built["base_commit"],
                            pol.get("digest", ""),
                            len(built.get("checks", [])),
                            int(cnt.get("PASS", 0)),
                            int(cnt.get("FAIL", 0)),
                            valid,
                            last_v.stat().st_mtime,  # when it was measured: reading an old verdict must not freshen it
                        ).to_dict()
                    )
                    seen.add(rid)


def gather_receipts(limit: int = 20) -> list[dict]:
    """The receipts on record: today the last verify's, the one that says what is true now."""
    records: list[dict] = []
    seen: set[str] = set()
    # The last verdict leads: a limit must never cut off the one receipt that says what is true now.
    _load_last_verify_receipt(seen, records)
    return records[:limit]


USAGE = (
    "usage: headron receipt snapshot   (one-screen background brain: totals, pass rate, touched files, open gates)\n"
    "       headron receipt verify <file> [--signed-by <identity> --trust <file> [--revoked <file>]]\n"
    "       headron receipt sign <file> --key <private key>   (-h/--help prints this)"
)


def _signing_options(argv: list[str]) -> dict[str, str] | None:
    """The options a command takes, or None when the command line is not one of the two in USAGE."""
    if len(argv) < 2 or argv[0] not in ("verify", "sign"):
        return None
    pairs = argv[2:]
    if len(pairs) % 2:
        return None
    options = dict(zip(pairs[::2], pairs[1::2], strict=True))
    signer = {"--signed-by", "--trust"}
    wanted = {"sign": [{"--key"}], "verify": [set(), signer, signer | {"--revoked"}]}[argv[0]]
    return options if set(options) in wanted and len(options) == len(pairs) // 2 else None


def _findings(command: str, path: Path, data: bytes, options: dict[str, str]) -> list[str]:
    """Only the signing paths load receiptsign, so a plain verify stays this one file."""
    if not options:
        return verify_bytes(data)
    import receiptsign  # noqa: PLC0415

    if command == "sign":
        return receiptsign.sign(path, Path(options["--key"]))
    revoked = Path(options["--revoked"]) if "--revoked" in options else None
    return receiptsign.verify_signed(path, options["--signed-by"], Path(options["--trust"]), revoked)


def snapshot(top_files: int = 10) -> dict:
    """The last verify's rows collapsed into one record a chat reads in a single call: totals, pass rate,
    the most-touched files, and the gates still open (FAIL / NOT RUN / SKIP).

    THE BACKGROUND BRAIN. A chat asked "where are we?" would otherwise parse every raw row; this is the
    one-screen answer. It reads the same marker `gather_receipts` does, so it is the current truth, never a
    freshened old verdict. A missing marker is an empty snapshot, not an error — no run is a real state."""
    marker = _marker_path()
    if not marker.is_file():
        return {"schema": 1, "command": "receipt snapshot", "measured_at": None, "total_checks": 0,
                "pass_rate": 0.0, "top_touched_files": [], "open_gates": [], "note": "no verify on record"}
    with contextlib.suppress(OSError, json.JSONDecodeError):
        data = json.loads(marker.read_text(encoding="utf-8"))
        rows = data.get("rows") or []
        tally = Counter(str(r.get("verdict")) for r in rows)
        total = len(rows)
        passed = tally.get("PASS", 0) + tally.get("REUSED", 0)
        files: Counter[str] = Counter()
        for row in rows:
            rid = str(row.get("id") or "")
            if ":" in rid:  # a per-target gate id names its file after the colon
                files[rid.split(":", 1)[1]] += 1
            for name in row.get("inputs") or []:
                files[str(name)] += 1
        open_gates = [
            {"id": r.get("id"), "verdict": r.get("verdict"), "why": r.get("why")}
            for r in rows
            if r.get("verdict") in ("FAIL", "NOT RUN", "SKIP")
        ]
        return {
            "schema": 1,
            "command": "receipt snapshot",
            "measured_at": data.get("measured_at") or marker.stat().st_mtime,
            "contract": data.get("contract"),
            "total_checks": total,
            "pass": tally.get("PASS", 0),
            "reused": tally.get("REUSED", 0),
            "fail": tally.get("FAIL", 0),
            "not_run": tally.get("NOT RUN", 0) + tally.get("SKIP", 0),
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "top_touched_files": files.most_common(top_files),
            "open_gates": open_gates,
        }
    return {"schema": 1, "command": "receipt snapshot", "measured_at": None, "total_checks": 0,
            "pass_rate": 0.0, "top_touched_files": [], "open_gates": [], "note": "unreadable marker"}


def main(argv: list[str]) -> int:
    if argv in (["-h"], ["--help"]):
        print(USAGE)
        return 0
    if argv[:1] == ["snapshot"]:
        print(json.dumps(snapshot(), indent=2))
        return 0
    options = _signing_options(argv)
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    data = Path(argv[1]).read_bytes()
    findings = _findings(argv[0], Path(argv[1]), data, options)
    if findings:
        for finding in findings:
            print(f"FAIL  {finding}")
        return 1
    receipt = json.loads(data)
    signed = f"  signed by {options['--signed-by']}" if "--signed-by" in options else ""
    wrote = f"  wrote {argv[1]}.sig" if argv[0] == "sign" else ""
    if receipt.get("kind") == COMPUTATION_KIND:
        print(
            f"ok    {receipt['receipt_id']}  computation {receipt['program']} v{receipt['version']}  status {receipt['status']}{signed}{wrote}"
        )
        return 0
    print(
        f"ok    {receipt['receipt_id']}  verdict {receipt['verdict']}  {len(receipt['checks'])} checks{signed}{wrote}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
