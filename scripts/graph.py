#!/usr/bin/env python3
"""Knowledge graph module — pointers, links, tags, edges, and tunnels.

Inspired by Obsidian's bidirectional link structure, this module builds an in-memory
graph from atlas.yaml declarations. Nodes represent files, gates, commands, verdicts and claims.
Edges represent relationships (depends_on, blocks, enables, references, rests_on). Tags categorize
nodes. Pointers are direct references. Tunnels are paths through multiple nodes.

The graph enables path-based reasoning: instead of checking gates sequentially, the engine
traverses the graph to find all affected gates in one pass.

proves: the graph built from atlas.yaml holds its gates, verdicts, edges and tunnels, and answers a lookup and a walk
does_not_prove: that a path is correct — only that it exists in the graph
closed_by: decide_test.py, which builds the graph and asserts its nodes, tags, tunnels and walk
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from atlascore import ROOT, atlas, rel, route_for, route_targets
from exrun import examples


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""

    FILE = "file"
    GATE = "gate"
    COMMAND = "command"
    VERDICT = "verdict"
    ROUTE = "route"
    INSTRUMENT = "instrument"
    CLAIM = "claim"
    RECORD = "record"


class EdgeType(Enum):
    """Types of edges in the knowledge graph."""

    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    ENABLES = "enables"
    REFERENCES = "references"
    ISOLATES = "isolates"
    FAST_TRACKS = "fast_tracks"
    RESTS_ON = "rests_on"


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
        old = self.nodes.get(node.id)
        if old:
            for tag in set(old.tags):
                self.tags[tag].remove(node.id)
        self.nodes[node.id] = node
        for tag in dict.fromkeys(node.tags):
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

            advanced = False
            for target, edge_type in self._adjacency.get(current, []):
                if target in path:
                    continue  # Avoid cycles
                if predicate and not predicate(target, edge_type):
                    continue
                advanced = True
                stack.append((target, path + [target], depth + 1))

            if not advanced:
                paths.append(path)

        return paths

    def get_by_tag(self, tag: str) -> list[str]:
        """Get all node ids with a given tag."""
        return self.tags.get(tag, [])

    def get_tunnels(self, source: str | None = None) -> list[Tunnel]:
        """Get tunnels, optionally filtered by source."""
        if source is None:
            return self.tunnels
        return [t for t in self.tunnels if t.path and t.path[0] == source]

    def distance(self, start: str, end: str, predicate: Callable | None = None) -> int | None:
        """Shortest path distance (in hops) between start and end. None if unreachable."""
        if start not in self.nodes or end not in self.nodes:
            return None
        if start == end:
            return 0
        from collections import deque

        visited = {start}
        queue = deque([(start, 0)])
        while queue:
            current, dist = queue.popleft()
            for target, edge_type in self._adjacency.get(current, []):
                if predicate and not predicate(target, edge_type):
                    continue
                if target == end:
                    return dist + 1
                if target not in visited:
                    visited.add(target)
                    queue.append((target, dist + 1))
        return None

    def shortest_path(self, start: str, end: str, predicate: Callable | None = None) -> list[str] | None:
        """Shortest node sequence connecting start to end. None if unreachable."""
        if start not in self.nodes or end not in self.nodes:
            return None
        if start == end:
            return [start]
        from collections import deque

        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            current, path = queue.popleft()
            for target, edge_type in self._adjacency.get(current, []):
                if predicate and not predicate(target, edge_type):
                    continue
                if target == end:
                    return path + [end]
                if target not in visited:
                    visited.add(target)
                    queue.append((target, path + [target]))
        return None

    def pointers_for(self, node_id: str) -> list[Pointer]:
        """All pointers originating from or pointing to node_id."""
        return [p for p in self.pointers if p.from_node == node_id or p.to_node == node_id]


# Module-level singleton, built once at import
_graph: Graph | None = None


def get_graph() -> Graph:
    """Get or build the knowledge graph singleton."""
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def _populate_decision_nodes(g: Graph, data: dict) -> None:
    tables = data.get("decision_tables") or {}
    for category, gates in (tables.get("gate_categories") or {}).items():
        for gate_id in gates:
            g.add_node(Node(id=gate_id, type=NodeType.GATE, tags=[category, "gate"], metadata={"category": category}))

    for verdict_name in tables.get("verdict_types") or {}:
        g.add_node(Node(id=str(verdict_name), type=NodeType.VERDICT, tags=["verdict"]))

    transitions = tables.get("transitions") or {}
    for state, verdict_map in transitions.items():
        g.add_node(Node(id=str(state), type=NodeType.COMMAND, tags=["state", "pipeline"]))
        for verdict, next_state in (verdict_map or {}).items():
            g.add_node(Node(id=str(next_state), type=NodeType.COMMAND, tags=["state", "pipeline"]))
            edge_type = EdgeType.ENABLES if str(verdict) == "pass" else EdgeType.BLOCKS
            g.add_edge(Edge(source=str(verdict), target=str(next_state), type=edge_type))
            g.add_edge(Edge(source=str(state), target=str(next_state), type=edge_type))


def _populate_forbidden_and_gates(g: Graph, data: dict) -> None:
    forbidden = data.get("forbidden_calls") or {}
    for rule_name, rule_spec in forbidden.items():
        g.add_node(Node(id=str(rule_name), type=NodeType.INSTRUMENT, tags=["forbidden", "rule"]))
        roster = (rule_spec or {}).get("roster", [])
        for r in roster:
            g.add_node(Node(id=str(r), type=NodeType.FILE, tags=["forbidden", rule_name]))
            g.add_edge(Edge(source=rule_name, target=str(r), type=EdgeType.ISOLATES))

    done_set = (data.get("verification_policy") or {}).get("done_set") or []
    for gate_spec in done_set:
        gate_id = str(gate_spec.get("id"))
        if gate_id not in g.nodes:
            g.add_node(Node(id=gate_id, type=NodeType.GATE, tags=["gate", "done_set"]))
        for dep in gate_spec.get("depends_on") or []:
            dep_id = str(dep)
            if dep_id not in g.nodes:
                g.add_node(Node(id=dep_id, type=NodeType.GATE, tags=["gate"]))
            g.add_edge(Edge(source=gate_id, target=dep_id, type=EdgeType.DEPENDS_ON))


def _populate_routes_and_instruments(g: Graph, data: dict) -> None:
    route_ids = {}
    for target in route_targets():
        route_id = f"route:{target}" if str(target) in g.nodes else str(target)
        route_ids[str(target)] = route_id
        g.add_node(Node(id=route_id, type=NodeType.ROUTE, tags=["route", "language"]))
        for doc in (
            f"languages/{target}/README.md",
            f"languages/{target}/OPERATING.md",
            f"languages/{target}/tools.yaml",
        ):
            if (ROOT / doc).is_file():
                g.add_node(Node(id=doc, type=NodeType.FILE, tags=["doc", str(target)]))
                g.add_edge(Edge(source=route_id, target=doc, type=EdgeType.REFERENCES))

    for path in examples():
        route_id = route_ids.get(route_for(str(path)))
        if route_id:
            name = rel(path)
            if name not in g.nodes:
                g.add_node(Node(id=name, type=NodeType.FILE, tags=["example"]))
            g.add_edge(Edge(source=route_id, target=name, type=EdgeType.REFERENCES))

    instruments = data.get("instruments") or {}
    for inst_name in instruments:
        if inst_name not in g.nodes:
            g.add_node(Node(id=str(inst_name), type=NodeType.INSTRUMENT, tags=["instrument"]))
    for inst_name, inst_data in instruments.items():
        closed_by = (inst_data or {}).get("closed_by", "").split(",")[0].split()[0]
        if closed_by and closed_by in instruments and closed_by != inst_name:
            g.add_edge(Edge(source=str(inst_name), target=str(closed_by), type=EdgeType.REFERENCES))

    runtimes = data.get("runtime_entry") or []
    for entry in runtimes:
        rid = entry.get("id")
        adapter = entry.get("adapter")
        loads = entry.get("loads", "AGENTS.md")
        if rid:
            g.add_node(Node(id=f"runtime:{rid}", type=NodeType.ROUTE, tags=["runtime", str(rid)]))
            if adapter and (ROOT / adapter).is_file():
                g.add_node(Node(id=adapter, type=NodeType.FILE, tags=["adapter", str(rid)]))
                g.add_edge(Edge(source=f"runtime:{rid}", target=adapter, type=EdgeType.REFERENCES))
            if loads and (ROOT / loads).is_file():
                if loads not in g.nodes:
                    g.add_node(Node(id=loads, type=NodeType.FILE, tags=["entry"]))
                g.add_edge(Edge(source=f"runtime:{rid}", target=loads, type=EdgeType.REFERENCES))
                g.add_pointer(Pointer(from_node=f"runtime:{rid}", to_node=loads, context=f"loads {loads}"))


def _populate_mind_and_tunnels(g: Graph, data: dict) -> None:
    transitions = (data.get("decision_tables") or {}).get("transitions") or {}
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

    mind_stages = ["classify", "plan", "route", "policy", "diagnose", "recover", "escalate", "refuse"]
    for stage in mind_stages:
        g.add_node(Node(id=f"mind.{stage}", type=NodeType.COMMAND, tags=["mind", "orchestration"]))
    for i in range(len(mind_stages) - 1):
        g.add_edge(Edge(source=f"mind.{mind_stages[i]}", target=f"mind.{mind_stages[i + 1]}", type=EdgeType.ENABLES))

    g.add_tunnel(
        Tunnel(
            name="mind/orchestration",
            path=[f"mind.{s}" for s in mind_stages],
            edges=[EdgeType.ENABLES] * (len(mind_stages) - 1),
        )
    )

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


def _populate_claims(g: Graph) -> None:
    """A claim node per docs/systems/claims.yaml entry; each dependent RESTS_ON the claim it names."""
    from claims import records, standing  # noqa: PLC0415

    claims = records()
    for name, spec in claims.items():
        g.add_node(
            Node(
                id=f"claim:{name}",
                type=NodeType.CLAIM,
                tags=["claim", standing(spec or {})],
                metadata={"label": (spec or {}).get("label"), "statement": (spec or {}).get("statement")},
            )
        )
    for name, spec in claims.items():
        for ref in (spec or {}).get("dependents") or []:
            if str(ref) not in g.nodes:
                g.add_node(Node(id=str(ref), type=NodeType.RECORD, tags=["record", str(ref).partition(":")[0]]))
            g.add_edge(Edge(source=str(ref), target=f"claim:{name}", type=EdgeType.RESTS_ON))


def _build_graph() -> Graph:
    """Build the knowledge graph from atlas.yaml declarations."""
    g = Graph()
    data = atlas()
    _populate_decision_nodes(g, data)
    _populate_forbidden_and_gates(g, data)
    _populate_routes_and_instruments(g, data)
    _populate_mind_and_tunnels(g, data)
    _populate_claims(g)
    return g
