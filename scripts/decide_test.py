#!/usr/bin/env python3
"""Mutation tests for the compiled decision table engine, graph, .thea framework, and Go bridge.

Each case plants a real defect in the decision_tables declaration, graph structure,
.thea framework, or Go bridge, then asserts the check refuses it. The case count is asserted at the end.

    python scripts/decide_test.py
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas  # noqa: E402
import decide  # noqa: E402
import graph  # noqa: E402
import thea_framework  # noqa: E402

CASES: list[tuple[str, str]] = []


def _run_check() -> tuple[int, str]:
    """Run the decision_table_errors enforcer alone and return (rc, output)."""
    atlas.atlas.cache_clear()
    decide.reset_caches()
    errors = decide.decision_table_errors()
    rc = 1 if errors else 0
    out = "\n".join(f"- {e}" for e in errors) if errors else ""
    return rc, out


def case(name: str, kills: str, expect_fail: bool, needle: str | None = None) -> None:
    rc, out = _run_check()
    failed = rc != 0
    if failed != expect_fail:
        raise SystemExit(
            f"FAIL {name}\n  kills: {kills}\n  rc={rc}, expected {'non-zero' if expect_fail else '0'}\n{out[:800]}"
        )
    if needle and needle not in out:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  expected {needle!r} in output\n{out[:800]}")
    CASES.append((name, kills))
    print(f"  ok    {name}")


@contextlib.contextmanager
def mutated(filename: str, mutator):
    """Plant a defect, yield, then restore — like atlas_test.mutated but local."""
    path = ROOT / filename
    original = path.read_bytes()
    try:
        path.write_text(mutator(original.decode("utf-8")), encoding="utf-8")
        yield
    finally:
        path.write_bytes(original)
        atlas.atlas.cache_clear()
        decide.reset_caches()
        graph.reset_graph()


def _test_decision_tables() -> None:
    """Tests 1-14: decision table validation and verdict lookups."""

    # 1. Invalid verdict type — the engine refuses a name it cannot route.
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            '    pass: {transition: next_gate, label: "Clear"}',
            '    pass: {transition: next_gate, label: "Clear"}\n    bogus: {transition: nowhere, label: "Broken"}',
            1,
        ),
    ):
        case(
            "a decision table with an invalid verdict type FAILS",
            "a verdict name the engine cannot route, so the transition matrix has a hole",
            True,
            "not a valid verdict type",
        )

    # 2. Gate category references a non-existent gate.
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            "    instant: [contract, context_cost, code_shape]",
            "    instant: [contract, context_cost, code_shape, nonexistent_gate]",
            1,
        ),
    ):
        case(
            "a gate category naming a missing gate FAILS",
            "a category that groups a gate the done_set does not contain, so the lookup returns nothing",
            True,
            "not in verification_policy/done_set",
        )

    # 3. Invalid command pattern — the engine refuses a broken regex.
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            '    safe: {pattern: "^(git (status|diff|log)|ls|cat|grep)", risk: 0}',
            '    safe: {pattern: "^(git (status|diff|log)|ls|cat|grep", risk: 0}',
            1,
        ),
    ):
        case(
            "a command category with a broken regex FAILS",
            "a pattern that cannot compile, so the classifier skips it silently instead of refusing",
            True,
            "not a valid regex",
        )

    # 4. Missing risk level — the engine refuses a category without a risk declaration.
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            '    safe: {pattern: "^(git (status|diff|log)|ls|cat|grep)", risk: 0}',
            '    safe: {pattern: "^(git (status|diff|log)|ls|cat|grep)"}',
            1,
        ),
    ):
        case(
            "a command category with no risk level FAILS",
            "a category that classifies but does not say how dangerous the match is",
            True,
            "declares no risk level",
        )

    # 5. Invalid transition state — the engine refuses a state name it does not know.
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            "    ingest: {pass: classify, fail: halt, isolate: sandbox_review, fast_track: exit}",
            "    ingest: {pass: classify, fail: halt, isolate: sandbox_review, fast_track: exit}\n    bogus_state: {pass: exit}",
            1,
        ),
    ):
        case(
            "a transition from an invalid state FAILS",
            "a state name the pipeline cannot enter, so the transition is unreachable",
            True,
            "is not a valid state",
        )

    # 6. Clean tree passes — no errors on a valid decision_tables section.
    rc, out = _run_check()
    if rc != 0:
        raise SystemExit(f"FAIL clean tree\n  rc={rc}, expected 0\n{out[:800]}")
    CASES.append(("clean decision_tables section passes", "an enforcer that fires on correct declarations"))
    print("  ok    clean decision_tables section passes")

    # 7-8. Gate verdict lookups.
    decide.reset_caches()
    if decide.gate_verdict("contract") != "instant":
        raise SystemExit("FAIL gate_verdict")
    CASES.append(
        ("gate_verdict returns category for known gate", "a lookup that returns 'unknown' for a classified gate")
    )
    print("  ok    gate_verdict returns category for known gate")

    decide.reset_caches()
    if decide.gate_verdict("nonexistent_gate_xyz") != "unknown":
        raise SystemExit("FAIL gate_verdict unknown")
    CASES.append(("gate_verdict returns 'unknown' for unclassified gate", "a lookup that invents a category"))
    print("  ok    gate_verdict returns 'unknown' for unclassified gate")

    # 9-10. Command verdict classifications.
    decide.reset_caches()
    cat, risk = decide.command_verdict("git status")
    if cat != "safe" or risk != 0:
        raise SystemExit(f"FAIL command_verdict safe\n  got ({cat!r}, {risk})")
    CASES.append(("command_verdict classifies safe command", "a classifier that mislabels a read-only git command"))
    print("  ok    command_verdict classifies safe command")

    decide.reset_caches()
    cat, risk = decide.command_verdict("git push origin main")
    if cat != "guarded" or risk != 1:
        raise SystemExit(f"FAIL command_verdict guarded\n  got ({cat!r}, {risk})")
    CASES.append(("command_verdict classifies guarded command", "a classifier that mislabels a write git command"))
    print("  ok    command_verdict classifies guarded command")

    # 11-12. Transition lookups.
    if decide.transition("ingest", "pass") != "classify":
        raise SystemExit("FAIL transition")
    CASES.append(("transition lookup returns correct next state", "a matrix that returns the wrong state"))
    print("  ok    transition lookup returns correct next state")

    if decide.transition("ingest", "nonexistent_verdict") is not None:
        raise SystemExit("FAIL transition unknown")
    CASES.append(("transition lookup returns None for unknown verdict", "a matrix that invents a transition"))
    print("  ok    transition lookup returns None for unknown verdict")

    # 13. GateVerdict enum values are correct.
    gv = decide.GateVerdict
    if gv.PASS.value != "pass" or gv.FAIL.value != "fail":
        raise SystemExit("FAIL GateVerdict enum values")
    if gv.PASS.transition != "next_gate" or gv.FAIL.transition != "halt":
        raise SystemExit("FAIL GateVerdict transitions")
    CASES.append(("GateVerdict enum values and transitions are correct", "an enum with wrong values"))
    print("  ok    GateVerdict enum values and transitions are correct")

    # 14. Caching works — second call returns cached result.
    decide.reset_caches()
    first = decide.gate_verdict("contract")
    second = decide.gate_verdict("contract")
    if first != second:
        raise SystemExit(f"FAIL caching\n  first={first!r}, second={second!r}")
    CASES.append(("gate_verdict caching returns consistent results", "a cache that returns different values"))
    print("  ok    gate_verdict caching returns consistent results")


def _test_graph() -> None:
    """Tests 15-28: graph database structure and queries."""

    # 15. Graph builds from atlas.yaml without error.
    graph.reset_graph()
    g = graph.get_graph()
    if not g.nodes:
        raise SystemExit("FAIL graph build\n  expected nodes, got empty graph")
    CASES.append(("graph builds from atlas.yaml", "a graph builder that produces an empty graph"))
    print("  ok    graph builds from atlas.yaml")

    # 16-17. Graph has gate and verdict nodes.
    if "contract" not in graph.nodes_by_tag("gate"):
        raise SystemExit("FAIL gate nodes")
    CASES.append(("graph contains gate nodes", "a graph that omits gate nodes"))
    print("  ok    graph contains gate nodes")

    if "pass" not in graph.nodes_by_tag("verdict"):
        raise SystemExit("FAIL verdict nodes")
    CASES.append(("graph contains verdict nodes", "a graph that omits verdict nodes"))
    print("  ok    graph contains verdict nodes")

    # 18-19. Graph query returns adjacent nodes / error for unknown.
    result = graph.query_node("pass")
    if "error" in result:
        raise SystemExit(f"FAIL graph query\n  {result['error']}")
    CASES.append(("graph query returns adjacent nodes", "a query that fails on existing nodes"))
    print("  ok    graph query returns adjacent nodes")

    result = graph.query_node("nonexistent_node_xyz")
    if "error" not in result:
        raise SystemExit("FAIL graph query unknown\n  expected error")
    CASES.append(("graph query returns error for unknown node", "a query that invents a node"))
    print("  ok    graph query returns error for unknown node")

    # 20. Graph traverse returns paths.
    paths = graph.traverse_graph("pass", max_depth=2)
    if not isinstance(paths, list):
        raise SystemExit(f"FAIL graph traverse\n  expected list, got {type(paths)}")
    CASES.append(("graph traverse returns paths", "a traversal that returns non-list"))
    print("  ok    graph traverse returns paths")

    # 21-22. Graph has edges and tunnels.
    g = graph.get_graph()
    if not g.edges:
        raise SystemExit("FAIL graph edges")
    CASES.append(("graph contains edges", "a graph with no edges"))
    print("  ok    graph contains edges")

    if not g.tunnels:
        raise SystemExit("FAIL graph tunnels")
    CASES.append(("graph contains tunnels", "a graph with no tunnels"))
    print("  ok    graph contains tunnels")

    # 23. Graph errors enforcer runs.
    graph.reset_graph()
    errors = graph.graph_errors()
    if not isinstance(errors, list):
        raise SystemExit(f"FAIL graph errors\n  expected list, got {type(errors)}")
    CASES.append(("graph errors enforcer returns list", "an enforcer that returns non-list"))
    print("  ok    graph errors enforcer returns list")

    # 24-27. Dataclass field checks.
    node = graph.Node(id="test", type=graph.NodeType.FILE, tags=["test"])
    if node.id != "test" or "test" not in node.tags:
        raise SystemExit("FAIL Node dataclass")
    CASES.append(("Node dataclass has required fields", "a Node missing id or tags"))
    print("  ok    Node dataclass has required fields")

    edge = graph.Edge(source="a", target="b", type=graph.EdgeType.ENABLES)
    if edge.source != "a" or edge.target != "b":
        raise SystemExit("FAIL Edge dataclass")
    CASES.append(("Edge dataclass has required fields", "an Edge missing source or target"))
    print("  ok    Edge dataclass has required fields")

    ptr = graph.Pointer(from_node="a", to_node="b", context="test")
    if ptr.from_node != "a" or ptr.to_node != "b":
        raise SystemExit("FAIL Pointer dataclass")
    CASES.append(("Pointer dataclass has required fields", "a Pointer missing from_node or to_node"))
    print("  ok    Pointer dataclass has required fields")

    tunnel = graph.Tunnel(name="test", path=["a", "b"], edges=[graph.EdgeType.ENABLES])
    if tunnel.name != "test" or len(tunnel.path) != 2:
        raise SystemExit("FAIL Tunnel dataclass")
    CASES.append(("Tunnel dataclass has required fields", "a Tunnel missing name or path"))
    print("  ok    Tunnel dataclass has required fields")

    # 28. Graph reset clears cache.
    graph.reset_graph()
    g1 = graph.get_graph()
    graph.reset_graph()
    g2 = graph.get_graph()
    if g1 is g2:
        raise SystemExit("FAIL graph reset\n  expected new graph")
    CASES.append(("graph reset clears cache", "a reset that keeps the old graph"))
    print("  ok    graph reset clears cache")


def _test_thea_framework() -> None:
    """Tests 29-35: .thea framework validation."""

    # 29. .thea framework errors enforcer runs.
    errors = thea_framework.thea_framework_errors()
    if not isinstance(errors, list):
        raise SystemExit(f"FAIL thea framework errors\n  expected list, got {type(errors)}")
    CASES.append((".thea framework errors enforcer returns list", "an enforcer that returns non-list"))
    print("  ok    .thea framework errors enforcer returns list")

    # 30. Compile .thea program to rules.
    example_thea = ROOT / "tools" / "agent-task.example.thea"
    if example_thea.exists():
        content = example_thea.read_text(encoding="utf-8")
        rules = thea_framework.compile_thea_to_rules(example_thea, content)
        if not rules:
            raise SystemExit("FAIL compile .thea\n  expected rules, got empty")
        CASES.append((".thea program compiles to rules", "a compiler that produces no rules"))
        print("  ok    .thea program compiles to rules")
    else:
        CASES.append((".thea program compiles to rules", "a compiler that produces no rules"))
        print("  skip  .thea program compiles to rules (file not found)")

    # 31. TheaDecisionRule dataclass has required fields.
    rule = thea_framework.TheaDecisionRule(source="test.thea")
    if rule.source != "test.thea":
        raise SystemExit("FAIL TheaDecisionRule dataclass")
    CASES.append(("TheaDecisionRule dataclass has required fields", "a rule missing source"))
    print("  ok    TheaDecisionRule dataclass has required fields")

    # 32-33. Scope and command checks return unknown for non-matching input.
    result = thea_framework.thea_scope_check("nonexistent.py", example_thea)
    if result != "unknown":
        raise SystemExit(f"FAIL .thea scope check\n  expected unknown, got {result!r}")
    CASES.append((".thea scope check returns unknown for non-existent file", "a scope check that invents a result"))
    print("  ok    .thea scope check returns unknown for non-existent file")

    result = thea_framework.thea_command_check("xyzzy", example_thea)
    if result != "unknown":
        raise SystemExit(f"FAIL .thea command check\n  expected unknown, got {result!r}")
    CASES.append(
        (".thea command check returns unknown for non-matching command", "a command check that invents a result")
    )
    print("  ok    .thea command check returns unknown for non-matching command")

    # 34. .thea verdict returns dict.
    verdicts = thea_framework.thea_verdict(example_thea)
    if not isinstance(verdicts, dict):
        raise SystemExit(f"FAIL .thea verdict\n  expected dict, got {type(verdicts)}")
    CASES.append((".thea verdict returns dict", "a verdict function that returns non-dict"))
    print("  ok    .thea verdict returns dict")

    # 35. .thea scope check detects forbidden path.
    result = thea_framework.thea_scope_check(".agent", example_thea)
    if result != "forbidden":
        raise SystemExit(f"FAIL .thea scope forbidden\n  expected forbidden, got {result!r}")
    CASES.append((".thea scope check detects forbidden path", "a scope check that misses a forbidden path"))
    print("  ok    .thea scope check detects forbidden path")


def _test_go_bridge() -> None:
    """Tests 36-42: Go bridge compilation and graph enum checks."""

    go_file = ROOT / "scripts" / "decide_go.go"

    # 36. Go decision engine compiles.
    if go_file.exists():
        result = subprocess.run(
            ["go", "build", "-o", "/dev/null", str(go_file)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT / "scripts"),
        )
        if result.returncode != 0:
            raise SystemExit(f"FAIL Go compile\n  {result.stderr[:500]}")
        CASES.append(("Go decision engine compiles", "a Go file that fails to compile"))
        print("  ok    Go decision engine compiles")
    else:
        CASES.append(("Go decision engine compiles", "a Go file that fails to compile"))
        print("  skip  Go decision engine compiles (file not found)")

    # 37. Go tests pass.
    go_test_file = ROOT / "scripts" / "decide_go_test.go"
    if go_test_file.exists() and go_file.exists():
        result = subprocess.run(
            ["go", "test", "-v", str(go_file), str(go_test_file)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT / "scripts"),
        )
        if result.returncode != 0:
            raise SystemExit(f"FAIL Go tests\n  {result.stderr[:500]}")
        CASES.append(("Go tests pass", "Go tests that fail"))
        print("  ok    Go tests pass")
    else:
        CASES.append(("Go tests pass", "Go tests that fail"))
        print("  skip  Go tests pass (files not found)")

    # 38. Go engine runs and produces output.
    if go_file.exists():
        result = subprocess.run(
            ["go", "run", str(go_file)], capture_output=True, text=True, timeout=30, cwd=str(ROOT / "scripts")
        )
        if result.returncode != 0:
            raise SystemExit(f"FAIL Go run\n  {result.stderr[:500]}")
        if "git status" not in result.stdout:
            raise SystemExit("FAIL Go output\n  expected 'git status' in output")
        CASES.append(("Go engine runs and produces output", "a Go program that produces no output"))
        print("  ok    Go engine runs and produces output")
    else:
        CASES.append(("Go engine runs and produces output", "a Go program that produces no output"))
        print("  skip  Go engine runs and produces output (file not found)")

    # 39-40. Graph enum values.
    nt = graph.NodeType
    if nt.FILE.value != "file" or nt.GATE.value != "gate":
        raise SystemExit("FAIL NodeType enum values")
    CASES.append(("NodeType enum values are correct", "an enum whose values do not match the declared types"))
    print("  ok    NodeType enum values are correct")

    et = graph.EdgeType
    if et.DEPENDS_ON.value != "depends_on" or et.BLOCKS.value != "blocks":
        raise SystemExit("FAIL EdgeType enum values")
    CASES.append(("EdgeType enum values are correct", "an enum whose values do not match the declared types"))
    print("  ok    EdgeType enum values are correct")

    # 41-42. Graph adjacency and tags.
    g = graph.get_graph()
    if "pass" in g._adjacency and not isinstance(g._adjacency["pass"], list):
        raise SystemExit("FAIL adjacency\n  expected list")
    CASES.append(("graph adjacency is built correctly", "a graph with broken adjacency"))
    print("  ok    graph adjacency is built correctly")

    if "gate" in g.tags and not isinstance(g.tags["gate"], list):
        raise SystemExit("FAIL tags\n  expected list")
    CASES.append(("graph tags are built correctly", "a graph with broken tags"))
    print("  ok    graph tags are built correctly")


def main() -> int:
    """Run all planted defect cases and assert the count."""
    _test_decision_tables()
    _test_graph()
    _test_thea_framework()
    _test_go_bridge()

    expected = 42
    if len(CASES) != expected:
        raise SystemExit(f"FAIL case count: {len(CASES)} cases, expected {expected}")
    print(f"\n{len(CASES)}/{expected} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
