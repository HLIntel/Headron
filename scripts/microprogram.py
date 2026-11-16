#!/usr/bin/env python3
"""The one microprogram contract: a named, versioned step that answers a context with a MicroResult.

A microprogram wraps an existing engine function (classify, search, the graph's edge-domain check)
without rewriting it, so every step reports the same four things: what it answered, how sure it is,
what it rests on, and whether it may be acted on. Reached as `headron mind --micro <name>`.

proves: every registered program answers with a declared status, and none of them raises
does_not_prove: that a program's answer is right; that is the wrapped function's own instrument
closed_by: microprogram_test.py, which plants an undeclared status, a raising program and each wrapper's refusal
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

# THE STATUSES, AND WHAT A CALLER MAY DO WITH EACH. Only "ok" may be acted on; the other three
# fail closed. "unknown" (could not decide) is kept apart from "refused" (decided no): reading
# one as the other is the trap enforce.py already records for pytest's exit 5.
STATUSES: dict[str, str] = {
    "ok": "answered; the output may be acted on",
    "unknown": "ran but could not decide; act as if refused and ask a stronger step",
    "refused": "decided no: the input or the checked state breaks the contract; evidence says why",
    "error": "the program raised; evidence names the exception, output is None",
}
ACTIONABLE = "ok"


@dataclass(frozen=True)
class MicroResult:
    """One program's answer. Construction refuses an undeclared status or a confidence outside [0, 1]."""

    program: str
    version: str
    status: str
    output: Any = None
    # None means the program measures no probability; a wrapper never invents one.
    confidence: float | None = None
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"undeclared status {self.status!r}; declared: {sorted(STATUSES)}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence!r} is outside [0, 1]")
        # frozen does not deep-freeze: a list passed as evidence would stay mutable.
        object.__setattr__(self, "evidence_refs", tuple(str(ref) for ref in self.evidence_refs))

    @property
    def actionable(self) -> bool:
        return self.status == ACTIONABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "program": self.program,
            "version": self.version,
            "status": self.status,
            "output": self.output,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
        }


class MicroProgram(Protocol):
    name: str
    version: str

    def run(self, context: Mapping[str, Any]) -> MicroResult: ...


class Classify:
    """mind.classify over context["files"]; an unclassifiable change is unknown, not ok."""

    name = "classify"
    version = "1"

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import mind  # noqa: PLC0415

        found = mind.classify({"files": list(context.get("files", ()))})
        return MicroResult(
            self.name,
            self.version,
            "unknown" if found.unknown else "ok",
            found.to_dict(),
            evidence_refs=found.matched_rules or found.files,
        )


class Search:
    """mind.search over context["query"]; an empty query is refused, zero hits is an ok answer."""

    name = "search"
    version = "1"

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import mind  # noqa: PLC0415

        query = str(context.get("query", "")).strip()
        if not query:
            return MicroResult(self.name, self.version, "refused", evidence_refs=("no query",))
        hits = mind.search(query, limit=int(context.get("limit", 5)))
        return MicroResult(
            self.name, self.version, "ok", hits, evidence_refs=tuple(hit.get("path", "") for hit in hits)
        )


class EdgeDomains:
    """graph.edge_violations over context["graph"] (default: the built graph); any violation refuses."""

    name = "graph.edges"
    version = "1"

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import graph  # noqa: PLC0415

        planted = context.get("graph")  # `is None`, not `or`: an empty Graph may be falsy
        violations = graph.edge_violations(graph.get_graph() if planted is None else planted)
        return MicroResult(
            self.name, self.version, "refused" if violations else "ok", violations, evidence_refs=tuple(violations)
        )


REGISTRY: dict[str, MicroProgram] = {program.name: program for program in (Classify(), Search(), EdgeDomains())}


def run(name: str, context: Mapping[str, Any] | None = None) -> MicroResult:
    """Run one registered program; never raises.

    proves: an unknown name is refused and a raising program becomes status "error" with its exception named
    does_not_prove: that the wrapped function's answer is right
    closed_by: microprogram_test.py, which plants an unknown name and a raising program
    """
    program = REGISTRY.get(name)
    if program is None:
        return MicroResult(name, "", "refused", evidence_refs=(f"no program {name!r}; registered: {sorted(REGISTRY)}",))
    try:
        return program.run(context or {})
    except Exception as exc:  # noqa: BLE001 - the contract turns every raise into a declared status
        return MicroResult(program.name, program.version, "error", evidence_refs=(f"{type(exc).__name__}: {exc}",))


def cli(name: str, args: list[str], as_json: bool) -> int:
    """`headron mind --micro <name> [args]`: exit 0 only for an actionable answer; `list` prints the registry.

    proves: the registry is reachable from the headron CLI and its exit code fails closed
    does_not_prove: that a caller reads the status rather than only the exit code
    closed_by: microprogram_test.py, which runs the CLI on each status
    """
    import json  # noqa: PLC0415

    if name == "list":
        rows = [{"name": p.name, "version": p.version} for p in REGISTRY.values()]
        print(json.dumps(rows) if as_json else "\n".join(f"{r['name']} {r['version']}" for r in rows))
        return 0
    result = run(name, {"files": args, "query": " ".join(args)})
    if as_json:
        print(json.dumps(result.to_dict(), default=str))
    else:
        print(f"{result.program} {result.status}: {STATUSES[result.status]}")
        print("\n".join(f"  {ref}" for ref in result.evidence_refs[:10]))
    return 0 if result.actionable else 1
