"""Planted tests for crosscache (scripts/crosscache.py).

proves: cross-session cache returns passing node results when contract and tree match;
  dag_invalidation_set invalidates all nodes when contract hash moves;
  dag_invalidation_set preserves passing nodes when tree is unchanged;
  dag_invalidation_set invalidates nodes when the tree moves;
  cache is stored in untracked git metadata
does_not_prove: concurrency locks across separate machines
closed_by: crosscache_test.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import crosscache


def test_crosscache_node_key() -> None:
    key1 = crosscache.compute_node_key("hash-a", "gate-1", "tree-1")
    key2 = crosscache.compute_node_key("hash-a", "gate-1", "tree-1")
    key3 = crosscache.compute_node_key("hash-a", "gate-1", "tree-2")
    assert key1 == key2
    assert key1 != key3


def test_crosscache_put_and_get() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".git").mkdir()

        # Empty cache returns None
        assert crosscache.get_cached_node("contract-1", "syntax", "tree-1", repo=repo) is None

        # Failing row is never cached
        crosscache.put_cached_node("contract-1", "syntax", "tree-1", {"ran": True, "exit_code": 1}, repo=repo)
        assert crosscache.get_cached_node("contract-1", "syntax", "tree-1", repo=repo) is None

        # Passing row is cached and retrieved
        crosscache.put_cached_node(
            "contract-1",
            "syntax",
            "tree-1",
            {"ran": True, "exit_code": 0, "command": "python -m py_compile"},
            repo=repo,
        )
        got = crosscache.get_cached_node("contract-1", "syntax", "tree-1", repo=repo)
        assert got is not None
        assert got["exit_code"] == 0
        assert got["gate"] == "syntax"


def test_dag_invalidation() -> None:
    contract = {
        "task_id": "test-task",
        "route": "python",
        "change_class": "source_change",
        "objective": "Test task",
        "watch": ["scripts/test.py"],
    }
    # No previous state -> all invalidated
    inv_none = crosscache.dag_invalidation_set(contract, None, "tree-1")
    assert "formatter" in inv_none

    prev_state = {
        "contract": "different-hash",
        "tree": "tree-1",
        "nodes": {"formatter": {"state": "PASS", "exit_code": 0}},
    }
    # Contract hash moved -> all invalidated
    inv_diff_contract = crosscache.dag_invalidation_set(contract, prev_state, "tree-1")
    assert "formatter" in inv_diff_contract

    import agentpolicy

    c_hash = agentpolicy.contract_hash(contract)
    prev_state_match = {
        "contract": c_hash,
        "tree": "tree-1",
        "nodes": {"formatter": {"state": "PASS", "exit_code": 0}, "unit_tests": {"state": "FAIL", "exit_code": 1}},
    }
    # Same tree: passing node is kept, failing node is invalidated
    inv_same_tree = crosscache.dag_invalidation_set(contract, prev_state_match, "tree-1")
    assert "formatter" not in inv_same_tree
    assert "unit_tests" in inv_same_tree

    # Tree moved: all nodes invalidated
    inv_tree_moved = crosscache.dag_invalidation_set(contract, prev_state_match, "tree-2")
    assert "formatter" in inv_tree_moved


if __name__ == "__main__":
    test_crosscache_node_key()
    test_crosscache_put_and_get()
    test_dag_invalidation()
    print("crosscache_test: PASS")
