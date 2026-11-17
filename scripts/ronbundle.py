#!/usr/bin/env python3
"""A `.ron` bundle: one task's contract, receipts and evidence as a directory that verifies from its own bytes.

WHY. A task's proof lived in three places: its obligations under HEADRON_HOME, its receipts wherever `verify
--receipt` wrote them, and its evidence in whatever the closes named. None of them travelled together, so a reviewer
on another machine could check a receipt but not what it was owed for. A bundle carries all three, and its manifest
names every file by digest, so one edited, added or missing byte is a finding.

  <name>.ron/
    manifest.json                    schema, kind, task, tree, {path: sha256} for every other file, bundle_id
    contract.json                    the task's obligations as the ledger folded them when it was packed
    receipts/<file>.json             receipts from `headron verify --receipt`, each re-checked by receipt.verify_bytes
    evidence/<file>                  any other file a close names
    signatures/manifest.json.sig     optional: ssh-keygen over manifest.json's exact bytes, namespace headron-ron

INTEGRITY, NOT AUTHENTICITY, NOT DONE. bundle_id detects an edited manifest and the digests an edited file; whoever
edits one can recompute both, so only the signature, checked against the reader's own trust list, names who packed
it. An intact bundle is not a finished task: standing is reported apart, and an obligation is proven only while its
evidence covers the tree read, the bundle's own tree by default or, with --tree, the checkout the reader stands in.
Verifying reads no repository and imports only the standard library, receipt.py and receiptsign.py.

  python scripts/ronbundle.py pack <task> <out>.ron [--receipt FILE]... [--evidence FILE]... [--key PRIVATE_KEY]
  python scripts/ronbundle.py verify <bundle>.ron [--tree] [--signed-by ID --trust FILE [--revoked FILE]]

  exit 0 intact, and every obligation proven on the tree read; 1 an integrity or signature finding;
       3 intact, but an obligation is open, its evidence is not in the bundle or names a receipt that did not
         pass, or its evidence does not cover the tree read; 2 usage

proves: every file in the bundle is the one packed, none was added or removed, every receipt in it still verifies,
  a proven obligation counts only when its evidence ref names a file in the bundle and a receipt it names passed,
  and with --signed-by that the reader's trusted, unrevoked key signed exactly this manifest
does_not_prove: that the checks ran as the receipts say, that a receipt was made on the contract's tree (a receipt
  names a commit, the contract a tree id; binding them needs a receipt schema bump), or that an evidence file checks
  what its obligation states;
  the procedures the contract names are the instruments
closed_by: receiptsign_test.py (ron_cases), which plants an edited, an unlisted and a missing file, a symlink, a `..`
  path, a tampered receipt, a manifest re-digested over a wrong hash, a stale tree, a wrong signer, evidence held
  outside the bundle and a proven obligation whose receipt answers FAIL
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Container, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from receipt import _unique_pairs, digest, verify_bytes
from receiptsign import sign_detached, verify_detached

SCHEMA = 1
KIND = "headron.ron"
NAMESPACE = "headron-ron"  # a bundle signature must never verify as a receipt signature, nor the reverse
MANIFEST = "manifest.json"
CONTRACT = "contract.json"
SIGNATURE = "signatures/manifest.json.sig"
MANIFEST_KEYS = {"schema", "kind", "task", "tree", "files", "bundle_id"}
STATES = ("pending", "not-run", "unknown", "proven")  # obligations.STATES; ron_cases asserts they agree
UNKNOWN_TREE = "unknown-tree"  # obligations.UNKNOWN_TREE
SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}")
HEX64 = re.compile(r"[0-9a-f]{64}")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dump(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def path_problem(rel: str) -> str | None:
    """Why a manifest path may not name a bundle file, or None: contract.json, receipts/<f>.json or evidence/<f>."""
    parts = PurePosixPath(rel).parts
    if rel != PurePosixPath(rel).as_posix() or not all(SEGMENT.fullmatch(part) for part in parts):
        return f"{rel!r} is not a plain relative path"
    if parts == (CONTRACT,) or (len(parts) == 2 and parts[0] == "evidence"):
        return None
    if len(parts) == 2 and parts[0] == "receipts" and parts[1].endswith(".json"):
        return None
    return f"{rel!r} is outside contract.json, receipts/<file>.json and evidence/<file>"


def standing(rows: list[dict[str, Any]], now: str, unbound: Container[str] = ()) -> tuple[int, str]:
    """(proven count, first open obligation id or ""), by obligations.standing's rule: proven only while the
    evidence covers `now`, and nothing covers an unknown or a dirty tree. An id in `unbound` (evidence_problems)
    is open: its evidence is not in the bundle, or names a receipt that did not pass."""
    covered = now != UNKNOWN_TREE and not now.endswith("+dirty")
    proven = [
        row
        for row in rows
        if row["state"] == "proven" and covered and row.get("tree") == now and row["id"] not in unbound
    ]
    first_open = next((row["id"] for row in rows if row not in proven), "")
    return len(proven), first_open


def evidence_problems(bundle: Path, rows: list[dict[str, Any]]) -> dict[str, str]:
    """{obligation id: why} for each proven row whose evidence does not hold inside the bundle.

    The ledger's evidence is a free string; pack stores a file as receipts/<name> or evidence/<name>. A ref holds
    when it is one of those paths, or its last segment names exactly one, and when that file is a receipt, its verdict is
    PASS (status ok for a computation receipt). Read after verify(): every listed file already matches its digest."""
    files = json.loads((bundle / MANIFEST).read_bytes())["files"]
    found: dict[str, str] = {}
    for row in rows:
        if row["state"] != "proven":
            continue
        ref = str(row.get("evidence") or "").strip()
        name = PurePosixPath(ref.replace("\\", "/")).name
        candidates = [rel for rel in (f"receipts/{name}", f"evidence/{name}") if rel in files]
        hits = [ref] if ref in candidates else candidates if ref != CONTRACT else []
        if not ref or not hits:
            found[row["id"]] = f"evidence {ref!r} is not in the bundle"
        elif len(hits) > 1:
            found[row["id"]] = f"evidence {ref!r} is ambiguous: {', '.join(hits)}"
        elif hits[0].startswith("receipts/"):
            held = json.loads((bundle / hits[0]).read_bytes())
            said = held.get("verdict", {"ok": "PASS"}.get(held.get("status"), held.get("status")))
            if said != "PASS":
                found[row["id"]] = f"{hits[0]} answers {said}, not PASS"
    return found


def pack(
    task: str,
    out: Path,
    receipts: Sequence[Path] = (),
    evidence: Sequence[Path] = (),
    key: Path | None = None,
    at: str | None = None,
) -> list[str]:
    """Write `out` from the task's ledger and the named files; findings, empty when written. Writes nothing on one."""
    import atomicfile  # noqa: PLC0415
    import obligations  # noqa: PLC0415  packing reads the ledger; verifying must not need it

    if out.suffix != ".ron" or out.exists() or out.is_symlink():
        return [f"{out} must be a new path ending in .ron; a bundle is never rewritten in place"]
    try:
        rows = obligations.current(task)
    except obligations.LedgerError as error:
        return [str(error)]
    if not rows:
        return [f"{task} records no obligations; a bundle with nothing owed proves nothing"]
    tree = obligations.tree() if at is None else at
    contract = {"task": task, "tree": tree, "obligations": [{"id": oid, **row} for oid, row in sorted(rows.items())]}
    payload: dict[str, bytes] = {CONTRACT: _dump(contract)}
    findings: list[str] = []
    for folder, sources in (("receipts", receipts), ("evidence", evidence)):
        for source in sources:
            rel = f"{folder}/{source.name}"
            if source.is_symlink() or not source.is_file():
                findings.append(f"{source} is not a regular file")
            elif rel in payload:
                findings.append(f"{source}: a second file by that name")
            elif problem := path_problem(rel):
                findings.append(f"{source}: {problem}")
            else:
                payload[rel] = source.read_bytes()
                if folder == "receipts":
                    findings += [f"{source}: {finding}" for finding in verify_bytes(payload[rel])]
    if findings:
        return findings
    body = {
        "schema": SCHEMA,
        "kind": KIND,
        "task": task,
        "tree": tree,
        "files": {rel: _sha(data) for rel, data in sorted(payload.items())},
    }
    manifest = _dump({**body, "bundle_id": digest(body)})
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".ron-", dir=out.parent))
    try:
        for rel, data in {**payload, MANIFEST: manifest}.items():
            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
            (stage / rel).write_bytes(data)
        if key is not None:
            (stage / SIGNATURE).parent.mkdir()
            if findings := sign_detached(manifest, key, stage / SIGNATURE, NAMESPACE):
                return findings
        atomicfile.move(stage, out)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return []


def _files(bundle: Path) -> tuple[set[str], list[str]]:
    """Every regular file under the bundle, relative and posix, and each entry that is not one."""
    found: set[str] = set()
    problems: list[str] = []
    for top, dirs, names in os.walk(bundle, followlinks=False):
        for name in [*dirs, *names]:
            entry = Path(top) / name
            rel = entry.relative_to(bundle).as_posix()
            if entry.is_symlink():
                problems.append(f"{rel} is a symlink; a bundle holds only regular files")
            elif name in names:
                if entry.is_file():
                    found.add(rel)
                else:
                    problems.append(f"{rel} is not a regular file")
    return found, problems


def _json(data: bytes, what: str) -> tuple[Any, list[str]]:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs), []
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        return None, [f"{what} is not JSON: {error}"]


def _manifest_problems(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        return [f"{MANIFEST} must hold exactly {sorted(MANIFEST_KEYS)}"]
    if manifest["schema"] != SCHEMA or manifest["kind"] != KIND:
        return [f"{MANIFEST} is not a {KIND} schema {SCHEMA} manifest"]
    if not isinstance(manifest["task"], str) or not isinstance(manifest["tree"], str):
        return [f"{MANIFEST} task and tree must be strings"]
    files = manifest["files"]
    if not isinstance(files, dict) or CONTRACT not in files:
        return [f"{MANIFEST} files must map paths to digests and name {CONTRACT}"]
    found = [problem for rel in files if (problem := path_problem(rel))]
    found += [f"{rel}: {value!r} is not a sha256" for rel, value in files.items() if not HEX64.fullmatch(str(value))]
    body = {k: v for k, v in manifest.items() if k != "bundle_id"}
    if manifest["bundle_id"] != digest(body):
        found.append(f"bundle_id does not recompute from {MANIFEST}; it was edited after packing")
    return found


def _contract_problems(contract: Any, manifest: dict[str, Any]) -> list[str]:
    if not isinstance(contract, dict) or set(contract) != {"task", "tree", "obligations"}:
        return [f"{CONTRACT} must hold exactly task, tree and obligations"]
    if (contract["task"], contract["tree"]) != (manifest["task"], manifest["tree"]):
        return [f"{CONTRACT} names another task or tree than {MANIFEST}"]
    rows = contract["obligations"]
    if not isinstance(rows, list) or not rows:
        return [f"{CONTRACT} lists no obligations"]
    found = []
    for row in rows:
        fields = ("id", "statement", "check", "state")
        if not isinstance(row, dict) or not all(isinstance(row.get(f), str) and row[f] for f in fields):
            found.append(f"{CONTRACT}: an obligation lacks one of {fields}")
        elif row["state"] not in STATES:
            found.append(f"{CONTRACT}: {row['id']} has state {row['state']!r}, outside {STATES}")
    return found


def verify(bundle: Path) -> tuple[list[str], dict[str, Any] | None]:
    """Each integrity finding, and the contract when there are none. Reads only the bundle's bytes."""
    if bundle.is_symlink() or not bundle.is_dir():
        return [f"{bundle} is not a bundle directory"], None
    present, findings = _files(bundle)
    if MANIFEST not in present:
        return [*findings, f"{MANIFEST} is missing"], None
    manifest, problems = _json((bundle / MANIFEST).read_bytes(), MANIFEST)
    findings += problems or _manifest_problems(manifest)
    if findings:
        return findings, None
    listed = set(manifest["files"])
    loose = present - listed - {MANIFEST, SIGNATURE}
    findings += [f"{rel} is not in {MANIFEST}" for rel in sorted(loose)]
    findings += [f"{rel} is listed but missing" for rel in sorted(listed - present)]
    for rel in sorted(listed & present):
        data = (bundle / rel).read_bytes()
        if _sha(data) != manifest["files"][rel]:
            findings.append(f"{rel} does not match its digest; it was edited after packing")
        elif rel.startswith("receipts/"):
            findings += [f"{rel}: {finding}" for finding in verify_bytes(data)]
    if findings:
        return findings, None
    contract, problems = _json((bundle / CONTRACT).read_bytes(), CONTRACT)
    findings = problems or _contract_problems(contract, manifest)
    return findings, None if findings else contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ronbundle", description=(__doc__ or "ronbundle").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pack_cmd = sub.add_parser("pack", help="write a bundle from a task's ledger and its receipts and evidence")
    pack_cmd.add_argument("task")
    pack_cmd.add_argument("out", type=Path)
    pack_cmd.add_argument("--receipt", type=Path, action="append", default=[])
    pack_cmd.add_argument("--evidence", type=Path, action="append", default=[])
    pack_cmd.add_argument("--key", type=Path, help="sign manifest.json with this private key")
    check = sub.add_parser("verify", help="check a bundle's bytes, then report its standing")
    check.add_argument("bundle", type=Path)
    check.add_argument("--tree", action="store_true", help="judge standing on the current checkout's tree")
    check.add_argument("--signed-by")
    check.add_argument("--trust", type=Path)
    check.add_argument("--revoked", type=Path)
    args = parser.parse_args(argv)
    if args.command == "pack":
        findings = pack(args.task, args.out, args.receipt, args.evidence, args.key)
        for finding in findings:
            print(f"FAIL  {finding}")
        if not findings:
            print(f"packed {args.out}")
        return 1 if findings else 0
    if bool(args.signed_by) != bool(args.trust):
        parser.error("--signed-by and --trust go together")
    findings, contract = verify(args.bundle)
    if contract is not None and args.signed_by:
        data = (args.bundle / MANIFEST).read_bytes()
        findings = verify_detached(data, args.bundle / SIGNATURE, args.signed_by, args.trust, args.revoked, NAMESPACE)
    for finding in findings:
        print(f"FAIL  {finding}")
    if findings or contract is None:
        return 1
    signed = "signature checked" if args.signed_by else "signed, not checked"
    print(f"INTEGRITY ok  {args.bundle} ({signed if (args.bundle / SIGNATURE).is_file() else 'unsigned'})")
    now = contract["tree"]
    if args.tree:
        import obligations  # noqa: PLC0415  only a reader standing in a checkout asks for its tree

        now = obligations.tree()
    unbound = evidence_problems(args.bundle, contract["obligations"])
    proven, first_open = standing(contract["obligations"], now, unbound)
    total = len(contract["obligations"])
    where = "the current tree" if args.tree else "the packed tree"
    print(f"STANDING {'proven' if not first_open else 'open'}  {proven}/{total} proven on {where} {now}")
    for oid, why in sorted(unbound.items()):
        print(f"OPEN  {oid}: {why}")
    if first_open:
        print(f"next: prove {first_open}, close it, then pack a new bundle")
    return 3 if first_open else 0


if __name__ == "__main__":
    sys.exit(main())
