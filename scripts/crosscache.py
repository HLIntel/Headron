"""Cross-session execution cache and task DAG incremental recomputation.

proves: a gate whose contract, inputs, and code are unchanged between sessions or task checkpoints
  reuses validated results without re-executing; an invalidated input or modified contract re-runs;
  the cross-session cache lives in untracked git metadata and never enters the repository tree
does_not_prove: that an external network resource has not changed when a gate does not declare it
closed_by: crosscache_test.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import atomicfile
from atlascore import ROOT, resolved_once, text_of
from safeedit import _git_path

SCHEMA = 1


def cache_path(repo: Path = ROOT) -> Path:
    """The cache lives inside the repository's git directory, so it survives sessions and is never tracked."""
    target_repo = Path(repo).resolve()
    if target_repo == resolved_once(ROOT):
        return _git_path("headron-execution-cache.json")
    return target_repo / ".git" / "headron-execution-cache.json"


def compute_node_key(contract_hash: str, gate: str, tree: str, inputs_digest: str | None = None) -> str:
    """A deterministic key for a task node: contract hash, gate identifier, and tree or inputs digest."""
    scope = inputs_digest or tree
    raw = f"{contract_hash}:{gate}:{scope}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_cache(repo: Path = ROOT) -> dict[str, Any]:
    path = cache_path(repo)
    if not path.is_file():
        return {"schema": SCHEMA, "entries": {}}
    try:
        data = json.loads(text_of(path))
        if data.get("schema") != SCHEMA or not isinstance(data.get("entries"), dict):
            return {"schema": SCHEMA, "entries": {}}
        return data
    except (OSError, json.JSONDecodeError):
        return {"schema": SCHEMA, "entries": {}}


def _write_cache(data: dict[str, Any], repo: Path = ROOT) -> None:
    path = cache_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomicfile.write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def get_cached_node(
    contract_hash: str, gate: str, tree: str, inputs_digest: str | None = None, repo: Path = ROOT
) -> dict[str, Any] | None:
    """Retrieve validated gate execution from the cross-session cache if one exists."""
    cache = _read_cache(repo)
    key = compute_node_key(contract_hash, gate, tree, inputs_digest)
    entry = cache.get("entries", {}).get(key)
    if isinstance(entry, dict) and entry.get("exit_code") == 0:
        return entry
    return None


def put_cached_node(
    contract_hash: str, gate: str, tree: str, row: dict[str, Any], inputs_digest: str | None = None, repo: Path = ROOT
) -> None:
    """Store a passing gate result in the cross-session cache."""
    if row.get("exit_code") != 0 or not row.get("ran"):
        return
    cache = _read_cache(repo)
    key = compute_node_key(contract_hash, gate, tree, inputs_digest)
    cache.setdefault("entries", {})[key] = {
        "gate": gate,
        "exit_code": 0,
        "ran": True,
        "command": row.get("command"),
        "contract": contract_hash,
        "tree": tree,
    }
    _write_cache(cache, repo)


def dag_invalidation_set(
    contract: dict[str, Any], previous_state: dict[str, Any] | None, current_tree: str
) -> set[str]:
    """Identify which nodes in a task DAG are invalidated and require recomputation.

    Returns the set of gate names that must re-execute. If previous_state is absent,
    or the contract changed, every required gate is invalidated.
    """
    import agentpolicy  # noqa: PLC0415

    required = [str(g) for g in agentpolicy.required_gates(contract)]
    if not previous_state:
        return set(required)

    prev_hash = previous_state.get("contract")
    curr_hash = agentpolicy.contract_hash(contract)
    if prev_hash != curr_hash:
        return set(required)

    prev_tree = previous_state.get("tree")
    prev_nodes = previous_state.get("nodes") or {}

    invalidated: set[str] = set()
    for gate in required:
        node = prev_nodes.get(gate)
        if not node or node.get("state") != "PASS" or node.get("exit_code") != 0:
            invalidated.add(gate)
            continue
        if prev_tree != current_tree:
            invalidated.add(gate)

    return invalidated
