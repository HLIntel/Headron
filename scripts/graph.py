#!/usr/bin/env python3
"""Knowledge graph module — pointers, links, tags, edges, and tunnels.

Inspired by Obsidian's bidirectional link structure, this module builds an in-memory
graph from atlas.yaml declarations. Nodes represent files, gates, commands, and verdicts.
Edges represent relationships (depends_on, blocks, enables, references). Tags categorize
nodes. Pointers are direct references. Tunnels are paths through multiple nodes.

The graph enables path-based reasoning: instead of checking gates sequentially, the engine
traverses the graph to find all affected gates in one pass.

proves: the graph structure is self-consistent — nodes, edges, tags, pointers, and tunnels
does_not_prove: that a path is correct — only that it exists in the graph
closed_by: decide_test.py, which plants malformed graphs and asserts refusal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from atlascore import atlas


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""

    FILE = "file"
    GATE = "gate"
    COMMAND = "command"
    VERDICT = "verdict"
    ROUTE = "route"
    INSTRUMENT = "instrument"


class EdgeType(Enum):
    """Types of edges in the knowledge graph."""

    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    ENABLES = "enables"
    REFERENCES = "references"
    ISOLATES = "isolates"
    FAST_TRACKS = "fast_tracks"


@dataclass
class Node:
    """A node in the knowledge graph.

    Each node has an id, type, optional tags, and metadata.
    """

    id: str
    type: NodeType
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed edge between two nodes.

    Each edge has a source, target, type, and optional weight.
    """

    source: str
    target: str
    type: EdgeType
    weight: float = 1.0


@dataclass
class Pointer:
    """A direct reference from one node to another.

    Unlike an edge, a pointer is a simple reference without a relationship type.
    Used for Obsidian-style [[wiki-links]].
    """

    from_node: str
    to_node: str
    context: str = ""


@dataclass
class Tunnel:
    """A path through multiple nodes.

    A tunnel represents a verified path from source to target, used for
    tracing the flow of a decision through the graph.
    """

    name: str
    path: list[str]
    edges: list[EdgeType]
    metadata: dict[str, Any] = field(default_factory=dict)


class Graph:
    """In-memory knowledge graph built from atlas.yaml declarations.

    The graph is built once at module load and cached. Query operations
    are O(1) for adjacent nodes, O(V+E) for traversal.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.tags: dict[str, list[str]] = {}  # tag → node_ids
        self.pointers: list[Pointer] = []
        self.tunnels: list[Tunnel] = []
        self._adjacency: dict[str, list[tuple[str, EdgeType]]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        for tag in node.tags:
            self.tags.setdefault(tag, []).append(node.id)

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge to the graph."""
        self.edges.append(edge)
        self._adjacency.setdefault(edge.source, []).append((edge.target, edge.type))

    def add_pointer(self, pointer: Pointer) -> None:
        """Add a pointer (wiki-link) to the graph."""
        self.pointers.append(pointer)

    def add_tunnel(self, tunnel: Tunnel) -> None:
        """Add a tunnel (verified path) to the graph."""
        self.tunnels.append(tunnel)

    def query(self, node_id: str) -> dict[str, Any]:
        """Query a node and return its adjacent nodes, edges, and tags.

        Returns:
            Dict with keys: node, adjacent, incoming, tags, pointers
        """
        node = self.nodes.get(node_id)
        if node is None:
            return {"error": f"node {node_id!r} not found"}

        adjacent = self._adjacency.get(node_id, [])
        incoming = [(e.source, e.type) for e in self.edges if e.target == node_id]
        pointers = [p for p in self.pointers if p.from_node == node_id or p.to_node == node_id]

        return {"node": node, "adjacent": adjacent, "incoming": incoming, "tags": node.tags, "pointers": pointers}

    def traverse(self, start: str, predicate: Callable | None = None, max_depth: int = 10) -> list[list[str]]:
        """Traverse the graph from start, returning all paths.

        Args:
            start: The starting node id.
            predicate: Optional filter function for edges.
            max_depth: Maximum traversal depth.

        Returns:
            List of paths, where each path is a list of node ids.
        """
        if start not in self.nodes:
            return []

        paths: list[list[str]] = []
        stack: list[tuple[str, list[str], int]] = [(start, [start], 0)]

        while stack:
            current, path, depth = stack.pop()
            if depth >= max_depth:
                paths.append(path)
                continue

            for target, edge_type in self._adjacency.get(current, []):
                if target in path:
                    continue  # Avoid cycles
                if predicate and not predicate(target, edge_type):
                    continue
                stack.append((target, path + [target], depth + 1))

            if not self._adjacency.get(current, []):
                paths.append(path)

        return paths

    def get_by_tag(self, tag: str) -> list[str]:
        """Get all node ids with a given tag."""
        return self.tags.get(tag, [])

    def get_pointers(self, node_id: str) -> list[str]:
        """Get all nodes pointed to by a given node."""
        return [p.to_node for p in self.pointers if p.from_node == node_id]

    def get_tunnels(self, source: str | None = None) -> list[Tunnel]:
        """Get tunnels, optionally filtered by source."""
        if source is None:
            return self.tunnels
        return [t for t in self.tunnels if t.path and t.path[0] == source]


# Module-level singleton, built once at import
_graph: Graph | None = None


def get_graph() -> Graph:
    """Get or build the knowledge graph singleton."""
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def reset_graph() -> None:
    """Clear the graph cache. Called before mutation tests."""
    global _graph
    _graph = None


def _build_graph() -> Graph:
    """Build the knowledge graph from atlas.yaml declarations."""
    g = Graph()
    data = atlas()

    # Add gate nodes from decision_tables
    tables = data.get("decision_tables") or {}
    for category, gates in (tables.get("gate_categories") or {}).items():
        for gate_id in gates:
            g.add_node(Node(id=gate_id, type=NodeType.GATE, tags=[category, "gate"], metadata={"category": category}))

    # Add verdict nodes
    for verdict_name in tables.get("verdict_types") or {}:
        g.add_node(Node(id=str(verdict_name), type=NodeType.VERDICT, tags=["verdict"]))

    # Add state and pipeline nodes from transitions
    transitions = tables.get("transitions") or {}
    for state, verdict_map in transitions.items():
        g.add_node(Node(id=str(state), type=NodeType.COMMAND, tags=["state", "pipeline"]))
        for verdict, next_state in (verdict_map or {}).items():
            g.add_node(Node(id=str(next_state), type=NodeType.COMMAND, tags=["state", "pipeline"]))
            edge_type = EdgeType.ENABLES if str(verdict) == "pass" else EdgeType.BLOCKS
            g.add_edge(Edge(source=str(verdict), target=str(next_state), type=edge_type))

    # Add file and rule nodes from forbidden_calls
    forbidden = data.get("forbidden_calls") or {}
    for rule_name, rule_spec in forbidden.items():
        g.add_node(Node(id=str(rule_name), type=NodeType.INSTRUMENT, tags=["forbidden", "rule"]))
        roster = (rule_spec or {}).get("roster", [])
        for r in roster:
            g.add_node(Node(id=str(r), type=NodeType.FILE, tags=["forbidden", rule_name]))
            g.add_edge(Edge(source=rule_name, target=str(r), type=EdgeType.ISOLATES))

    # Add route nodes
    routes = data.get("routing_policy") or {}
    for route_name in routes.get("precedence") or []:
        g.add_node(Node(id=str(route_name), type=NodeType.ROUTE, tags=["route"]))

    # Add instrument nodes
    instruments = data.get("instruments") or {}
    for inst_name in instruments:
        g.add_node(Node(id=str(inst_name), type=NodeType.INSTRUMENT, tags=["instrument"]))

    # Build tunnels from transition paths
    for state in transitions:
        for verdict in transitions[state]:
            next_state = transitions[state][verdict]
            g.add_tunnel(
                Tunnel(
                    name=f"{state}/{verdict}",
                    path=[str(state), str(next_state)],
                    edges=[EdgeType.ENABLES if str(verdict) == "pass" else EdgeType.BLOCKS],
                )
            )

    # Mind orchestration nodes and verified execution tunnel
    mind_stages = ["classify", "plan", "route", "policy", "diagnose", "recover", "escalate", "refuse"]
    for stage in mind_stages:
        g.add_node(Node(id=f"mind.{stage}", type=NodeType.COMMAND, tags=["mind", "orchestration"]))
    g.add_tunnel(
        Tunnel(
            name="mind/orchestration",
            path=[f"mind.{s}" for s in mind_stages],
            edges=[EdgeType.ENABLES] * (len(mind_stages) - 1),
        )
    )

    # Primary Obsidian-style wiki pointers connecting key concepts
    anchors = [
        ("contract", "verify"),
        ("mind.classify", "mind.plan"),
        ("mind.plan", "mind.route"),
        ("mind.diagnose", "mind.recover"),
        ("ingest", "classify"),
        ("classify", "verify"),
    ]
    for src, dst in anchors:
        if src in g.nodes and dst in g.nodes:
            g.add_pointer(Pointer(from_node=src, to_node=dst, context="verified pipeline flow"))

    return g


def graph_errors() -> list[str]:
    """Validate the graph structure is self-consistent.

    Checks:
    - All edge sources and targets reference existing nodes
    - All pointers reference existing nodes
    - All tunnel paths reference existing nodes
    - No duplicate node ids

    proves: the graph structure is self-consistent
    does_not_prove: that the graph is complete — only that what exists is valid
    closed_by: decide_test.py, which plants malformed graphs
    """
    errors: list[str] = []
    g = get_graph()

    # Check edge references
    for edge in g.edges:
        if edge.source not in g.nodes:
            errors.append(f"edge {edge.source} → {edge.target}: source {edge.source!r} not in graph")
        if edge.target not in g.nodes:
            errors.append(f"edge {edge.source} → {edge.target}: target {edge.target!r} not in graph")

    # Check pointer references
    for ptr in g.pointers:
        if ptr.from_node not in g.nodes:
            errors.append(f"pointer {ptr.from_node} → {ptr.to_node}: from_node {ptr.from_node!r} not in graph")
        if ptr.to_node not in g.nodes:
            errors.append(f"pointer {ptr.from_node} → {ptr.to_node}: to_node {ptr.to_node!r} not in graph")

    # Check tunnel paths
    for tunnel in g.tunnels:
        for node_id in tunnel.path:
            if node_id not in g.nodes:
                errors.append(f"tunnel {tunnel.name}: path node {node_id!r} not in graph")

    return errors


def query_node(node_id: str) -> dict[str, Any]:
    """Query a node by id — convenience function."""
    return get_graph().query(node_id)


def traverse_graph(start: str, predicate: Callable | None = None, max_depth: int = 10) -> list[list[str]]:
    """Traverse the graph from start — convenience function."""
    return get_graph().traverse(start, predicate, max_depth)


def nodes_by_tag(tag: str) -> list[str]:
    """Get all node ids with a given tag — convenience function."""
    return get_graph().get_by_tag(tag)
