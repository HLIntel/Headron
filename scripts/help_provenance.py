"""Headron Help answer provenance and freshness evaluator (contract v1).

Attaches exact file paths, byte sizes, sha256 digests, and line counts to factual claims.
Distinguishes live, stale, and unavailable evidence states without model hallucination.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def digest_file(path: Path) -> str:
    """Compute sha256 hex digest of file contents; empty string if unreadable."""
    if not path.is_file():
        return ""
    try:
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return ""


def build_provenance(path: Path, root: Path | None = None) -> dict[str, Any]:
    """Compile structured provenance record for a factual artifact."""
    if not path.is_file():
        return {"path": path.as_posix(), "exists": False, "status": "unavailable", "digest": "", "bytes": 0, "lines": 0}

    rel_str = path.relative_to(root).as_posix() if root and path.is_relative_to(root) else path.name
    try:
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        lines = len(content.splitlines())
        return {
            "path": rel_str,
            "exists": True,
            "status": "live",
            "digest": digest,
            "bytes": len(content),
            "lines": lines,
        }
    except OSError:
        return {"path": rel_str, "exists": False, "status": "unavailable", "digest": "", "bytes": 0, "lines": 0}


def evaluate_freshness(cached_digest: str, path: Path) -> str:
    """Return freshness state: live, stale, or unavailable."""
    if not path.is_file():
        return "unavailable"
    current_digest = digest_file(path)
    if not current_digest:
        return "unavailable"
    return "live" if current_digest == cached_digest else "stale"


def verify_provenance(provenance_record: dict[str, Any], root: Path) -> bool:
    """Verify whether a recorded provenance entry is still byte-identical to disk."""
    if not provenance_record.get("exists", False):
        return False
    target = root / provenance_record.get("path", "")
    recorded_digest = provenance_record.get("digest", "")
    return evaluate_freshness(recorded_digest, target) == "live"


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for provenance compilation and freshness evaluation."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Headron Help provenance compiler")
    parser.add_argument("path", help="File path to compile provenance for")
    parser.add_argument("--json", action="store_true", help="Print provenance as JSON")
    parser.add_argument("--check-fresh", metavar="DIGEST", help="Check freshness against cached digest")
    args = parser.parse_args(argv)

    target = Path(args.path)
    if args.check_fresh:
        st = evaluate_freshness(args.check_fresh, target)
        print(st)
        return 0

    prov = build_provenance(target)
    if args.json:
        print(json.dumps(prov, indent=2))
    else:
        print(f"Path: {prov['path']} ({prov['status']}) | Bytes: {prov['bytes']} | Digest: {prov['digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
