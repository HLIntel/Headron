#!/usr/bin/env python3
"""The one microprogram contract: a named, versioned step that answers a context with a MicroResult.

A microprogram wraps an existing engine function (classify, search, the graph's edge-domain check)
without rewriting it, so every step reports the same four things: what it answered, how sure it is,
what it rests on, and whether it may be acted on. Reached as `headron mind --micro <name>`.

Every result that may not be acted on names the next step to try (`next`); every step has a stop
condition (`timeout_s`, enforced by run()); and run() stamps each result's latency and counts each
program's statuses, so a caller can see which step is slow or keeps refusing.

proves: every registered program answers with a declared status within its timeout, and none of them raises
does_not_prove: that a program's answer is right; that is the wrapped function's own instrument
closed_by: microprogram_test.py, which plants an undeclared status, a raising program, each wrapper's refusal,
    a refusal with no next step, a hung step, a self-stamped latency and the status counters
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
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
# A program that declares no timeout_s gets this stop condition; none runs unbounded.
DEFAULT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class MicroResult:
    """One program's answer. Construction refuses an undeclared status, a confidence outside [0, 1], or a
    result that may not be acted on but names no next step."""

    program: str
    version: str
    status: str
    output: Any = None
    # None means the program measures no probability; a wrapper never invents one.
    confidence: float | None = None
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    # What to try next. REQUIRED when status is not ok: a refusal that does not say what to do is a dead end.
    next: str | None = None
    # Wall-clock latency in milliseconds. Stamped by run(), never by the program: a value set here is replaced.
    elapsed_ms: float | None = None
    # Computation receipt binding inputs, version, outputs, and verification results.
    receipt: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"undeclared status {self.status!r}; declared: {sorted(STATUSES)}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence!r} is outside [0, 1]")
        if self.status != ACTIONABLE and not (self.next or "").strip():
            raise ValueError(f"status {self.status!r} names no next step; every non-ok result says what to try next")
        # frozen does not deep-freeze: a list passed as evidence would stay mutable.
        object.__setattr__(self, "evidence_refs", tuple(str(ref) for ref in self.evidence_refs))

    @property
    def actionable(self) -> bool:
        return self.status == ACTIONABLE

    def to_dict(self) -> dict[str, Any]:
        result = {
            "program": self.program,
            "version": self.version,
            "status": self.status,
            "output": self.output,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "next": self.next,
            "elapsed_ms": self.elapsed_ms,
        }
        if self.receipt is not None:
            result["receipt"] = self.receipt
        return result


class MicroProgram(Protocol):
    name: str
    version: str
    timeout_s: float

    def run(self, context: Mapping[str, Any]) -> MicroResult: ...


class Classify:
    """mind.classify over context["files"]; an unclassifiable change is unknown, not ok."""

    name = "classify"
    version = "1"
    timeout_s = 10.0

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import mind  # noqa: PLC0415

        found = mind.classify({"files": list(context.get("files", ()))})
        return MicroResult(
            self.name,
            self.version,
            "unknown" if found.unknown else "ok",
            found.to_dict(),
            evidence_refs=found.matched_rules or found.files,
            next="name the changed files, or add a classifier rule for this path in mind.py" if found.unknown else None,
        )


class Search:
    """mind.search over context["query"]; an empty query is refused, zero hits is an ok answer."""

    name = "search"
    version = "1"
    timeout_s = 30.0

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import mind  # noqa: PLC0415

        query = str(context.get("query", "")).strip()
        if not query:
            return MicroResult(
                self.name, self.version, "refused", evidence_refs=("no query",), next="pass a non-blank query"
            )
        hits = mind.search(query, limit=int(context.get("limit", 5)))
        return MicroResult(
            self.name, self.version, "ok", hits, evidence_refs=tuple(hit.get("path", "") for hit in hits)
        )


class EdgeDomains:
    """graph.edge_violations over context["graph"] (default: the built graph); any violation refuses."""

    name = "graph.edges"
    version = "1"
    timeout_s = 30.0

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import graph  # noqa: PLC0415

        planted = context.get("graph")  # `is None`, not `or`: an empty Graph may be falsy
        violations = graph.edge_violations(graph.get_graph() if planted is None else planted)
        return MicroResult(
            self.name,
            self.version,
            "refused" if violations else "ok",
            violations,
            evidence_refs=tuple(violations),
            next="fix or drop each listed edge so its endpoints hold the declared domains" if violations else None,
        )


def mcnemar_exact(helped: int, hurt: int) -> float:
    """Two-sided exact McNemar p over the discordant pairs; no discordant pair is p 1.0, not a pass."""
    from math import comb  # noqa: PLC0415

    pairs = helped + hurt
    if pairs == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(pairs, i) for i in range(min(helped, hurt) + 1)) / 2**pairs)


def credit_store() -> Path:
    """The append-only credit log. Under HEADRON_HOME, never in the tree: a measurement is derived output."""
    from atlascore import headron_home  # noqa: PLC0415

    return headron_home() / "context-credit.jsonl"


class ContextCredit:
    """Counterfactual credit per handed-in context item: solved with every item minus solved without that one.

    context: {"shape": task shape, "full": [run], "without": {item: [run]}, "record": bool}. A run is what
    agentbench.run returns plus its "seed". Relevance chose the items; this scores whether each one changed
    the verdict (MemCredit's U(m, s) = R(M) - R(M minus m)). Pure over recorded runs: it never starts an agent.
    """

    name = "context.credit"
    version = "1"
    timeout_s = 10.0  # pure arithmetic over recorded runs; the append is the only I/O

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        shape, full = str(context.get("shape", "")).strip(), list(context.get("full", ()))
        without: Mapping[str, list[Mapping[str, Any]]] = context.get("without") or {}
        if not shape or not full or not without:
            return MicroResult(
                self.name,
                self.version,
                "refused",
                evidence_refs=("needs a shape, full runs and without runs",),
                next="pass a task shape, the full-context runs and each item's without-runs",
            )
        # AN ERRORED RUN IS NOT AN UNSOLVED RUN: agentbench scores a timeout solved=False, so reading it as a
        # verdict would credit the removed item +1 for an outage.
        errored = [f"full seed {r.get('seed')}" for r in full if r.get("agent_error")] + [
            f"{item} seed {r.get('seed')}" for item, runs in without.items() for r in runs if r.get("agent_error")
        ]
        if errored:
            return MicroResult(
                self.name,
                self.version,
                "unknown",
                evidence_refs=tuple(f"agent error: {e}" for e in errored),
                next="re-run the errored seeds; an outage is not a verdict",
            )
        solved = {r["seed"]: bool(r["solved"]) for r in full}
        credits: dict[str, dict[str, Any]] = {}
        for item, runs in without.items():
            dropped = {r["seed"]: bool(r["solved"]) for r in runs}
            if set(dropped) != set(solved) or len(runs) != len(dropped) or len(full) != len(solved):
                return MicroResult(
                    self.name,
                    self.version,
                    "refused",
                    evidence_refs=(f"{item}: seeds {sorted(dropped)} do not pair once each with {sorted(solved)}",),
                    next="record one run per full-context seed for this item, then score again",
                )
            helped = sum(solved[s] and not dropped[s] for s in solved)  # McNemar b: solved only with the item
            hurt = sum(dropped[s] and not solved[s] for s in solved)  # McNemar c: solved only without it
            credits[item] = {
                "credit": (helped - hurt) / len(solved),
                "helped": helped,
                "hurt": hurt,
                "pairs": len(solved),
                "p": mcnemar_exact(helped, hurt),
            }
        if context.get("record"):
            import json  # noqa: PLC0415

            store = credit_store()
            store.parent.mkdir(parents=True, exist_ok=True)
            with store.open("a", encoding="utf-8") as log:  # append, never rewrite: earlier credits stay as measured
                for item, row in credits.items():
                    log.write(json.dumps({"item": item, "shape": shape, "version": self.version, **row}) + "\n")
        return MicroResult(self.name, self.version, "ok", credits, evidence_refs=tuple(sorted(credits)))


class TaskObligations:
    """Whether a task may be called done: every obligation in its ledger (scripts/obligations.py) is proven on
    the tree being read. context: {"task": slug} (or the CLI's first arg), optional "root" (the repo, default
    cwd) or "tree" to read against.

    ok when all are proven on this tree; refused when one is pending or not-run, naming the first open one and
    its procedure; unknown when only stale-tree evidence stands, nothing is recorded, or the ledger is corrupt.
    """

    name = "task.obligations"
    version = "1"
    timeout_s = 30.0  # two git calls and one file read

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import obligations  # noqa: PLC0415

        task = str(context.get("task") or next(iter(context.get("args") or ()), "")).strip()
        if not task:
            return MicroResult(
                self.name, self.version, "refused", evidence_refs=("no task named",), next="pass the task slug"
            )
        try:
            root = Path(context["root"]) if context.get("root") else None
            now = str(context.get("tree") or obligations.tree(root))
            status, rows, next_step = obligations.report(task, now)
        except obligations.LedgerError as error:
            return MicroResult(
                self.name, self.version, "unknown", evidence_refs=(str(error),), next="repair the ledger line it names"
            )
        refs = tuple(f"{row['state']} {oid}" for oid, row in rows.items()) + (f"tree {now}",)
        return MicroResult(self.name, self.version, status, rows, evidence_refs=refs, next=next_step or None)


class MemoryValidate:
    """Whether a remembered claim (docs/systems/claims.yaml) may be served as a fact now: claims.validity.
    context: {"claim": name} (or the CLI's first arg), optional "claims" and "root" to read another registry.

    ok only while the claim can be shown to hold; refused when it is refuted or names no claim, naming its
    successor if it has one; unknown, with next "rediscover", when its validity cannot be established.
    """

    name = "memory.validate"
    version = "1"
    timeout_s = 30.0  # one registry read and at most one git diff

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import claims  # noqa: PLC0415

        name = str(context.get("claim") or next(iter(context.get("args") or ()), "")).strip()
        if not name:
            return MicroResult(
                self.name, self.version, "refused", evidence_refs=("no claim named",), next="pass a claim name"
            )
        root = Path(context.get("root") or claims.ROOT)
        registry = context.get("claims")
        status, why, next_step = claims.validity(name, registry if registry is not None else None, root)
        spec = (registry if registry is not None else claims.records(root)).get(name) or {}
        output = {"statement": spec.get("statement"), "label": spec.get("label")} if status == "ok" else None
        return MicroResult(
            self.name, self.version, status, output, evidence_refs=(f"claim:{name}", why), next=next_step or None
        )


class RonVerify:
    """Whether a .ron bundle (scripts/ronbundle.py) proves its task done: intact, then every obligation in its
    contract proven on the tree read. context: {"bundle": path} (or the CLI's first arg), optional "tree" to read
    against; the default is the tree the bundle was packed on.

    refused when the bundle has an integrity finding or an obligation is still open, naming the first; unknown
    when every obligation is proven but on another tree; ok only when intact and all proven on this tree. The
    signature is not read here: authorship is `python scripts/ronbundle.py verify --signed-by`.
    """

    name = "ron.verify"
    version = "1"
    timeout_s = 30.0  # one directory walk and a digest per file

    def run(self, context: Mapping[str, Any]) -> MicroResult:
        import ronbundle  # noqa: PLC0415

        bundle = str(context.get("bundle") or next(iter(context.get("args") or ()), "")).strip()
        if not bundle:
            return MicroResult(
                self.name, self.version, "refused", evidence_refs=("no bundle named",), next="pass a .ron path"
            )
        findings, contract = ronbundle.verify(Path(bundle))
        if contract is None:  # verify returns no contract whenever it has a finding
            return MicroResult(
                self.name,
                self.version,
                "refused",
                evidence_refs=tuple(findings) or ("no contract read",),
                next="repack it from the ledger; a bundle with a finding proves nothing",
            )
        rows = contract["obligations"]
        now = str(context.get("tree") or contract["tree"])
        proven, first_open = ronbundle.standing(rows, now)
        refs = (f"task {contract['task']}", f"{proven}/{len(rows)} proven on {now}")
        if not first_open:
            output = {"task": contract["task"], "tree": now, "proven": proven}
            return MicroResult(self.name, self.version, "ok", output, evidence_refs=refs)
        unproven = next((row["id"] for row in rows if row["state"] != "proven"), "")
        status = "refused" if unproven else "unknown"
        next_step = (
            f"prove {unproven}, close it, then pack a new bundle"
            if unproven
            else f"every obligation is proven, but not on {now}: re-prove them there, then pack a new bundle"
        )
        return MicroResult(self.name, self.version, status, evidence_refs=(*refs, f"open {first_open}"), next=next_step)


from computation_contract import ComputationContract  # noqa: E402
from compute_compose import Compose  # noqa: E402
from domain_reconcile import Reconcile  # noqa: E402
from finance import Finance  # noqa: E402

REGISTRY: dict[str, MicroProgram] = {
    program.name: program
    for program in (
        Classify(),
        Search(),
        EdgeDomains(),
        ContextCredit(),
        TaskObligations(),
        MemoryValidate(),
        RonVerify(),
        Finance(),
        Reconcile(),
        Compose(),
        ComputationContract(),
    )
}


# PER-STEP TELEMETRY, this process only: counts[program][status] and latency per program. A name that is not
# registered counts under UNREGISTERED, so a caller's typos cannot grow the table without bound.
UNREGISTERED = "(unregistered)"
_STATS_LOCK = threading.Lock()
_COUNTS: dict[str, dict[str, int]] = {}
_LATENCY_MS: dict[str, dict[str, float]] = {}


def _record(key: str, result: MicroResult, started: float, context: Mapping[str, Any] | None = None) -> MicroResult:
    stamped = replace(result, elapsed_ms=round((time.perf_counter() - started) * 1000, 3))
    if stamped.receipt is None:
        import receipt as receipt_mod  # noqa: PLC0415

        stamped = replace(
            stamped,
            receipt=receipt_mod.build_computation_receipt(
                program=stamped.program or key,
                version=stamped.version or "1",
                inputs=context or {},
                outputs=stamped.output,
                status=stamped.status,
                verification={
                    "status": "PASS" if stamped.status == "ok" else "FAIL",
                    "checks": [
                        {
                            "id": f"{stamped.program or key}.status",
                            "state": "PASS" if stamped.status == "ok" else "FAIL",
                        }
                    ],
                },
                evidence_refs=stamped.evidence_refs,
            ),
        )
    elapsed = stamped.elapsed_ms or 0.0
    with _STATS_LOCK:
        by_status = _COUNTS.setdefault(key, dict.fromkeys(STATUSES, 0))
        by_status[stamped.status] += 1
        latency = _LATENCY_MS.setdefault(key, {"total": 0.0, "max": 0.0})
        latency["total"] += elapsed
        latency["max"] = max(latency["max"], elapsed)
    return stamped


def stats() -> dict[str, dict[str, Any]]:
    """Per-program status counts and latency (total/max ms) for every run() in this process."""
    with _STATS_LOCK:
        return {
            key: {
                "counts": dict(_COUNTS[key]),
                "total_ms": round(_LATENCY_MS[key]["total"], 3),
                "max_ms": round(_LATENCY_MS[key]["max"], 3),
            }
            for key in sorted(_COUNTS)
        }


def _bounded(program: MicroProgram, context: Mapping[str, Any]) -> MicroResult:
    """Run the program on a daemon thread and wait at most its timeout_s.

    A Python thread cannot be killed, so an overrun step is abandoned, not stopped: it is a daemon, so it
    cannot hold the process open, and it writes only to its own holder, never to the counters.
    """
    timeout_s = float(getattr(program, "timeout_s", DEFAULT_TIMEOUT_S))
    holder: dict[str, Any] = {}

    def target() -> None:
        try:
            holder["result"] = program.run(context)
        except BaseException as exc:  # noqa: BLE001 - carried back to the caller, raised nowhere
            holder["error"] = exc

    worker = threading.Thread(target=target, name=f"micro:{program.name}", daemon=True)
    worker.start()
    worker.join(timeout_s)
    if worker.is_alive():
        return MicroResult(
            program.name,
            program.version,
            "unknown",
            evidence_refs=(f"timeout after {timeout_s:g}s",),
            next=f"retry with a narrower context, or raise {program.name}'s timeout_s if the step is just slow",
        )
    if "error" in holder:
        error = holder["error"]
        if isinstance(error, Exception):
            raise error
        raise RuntimeError(f"{type(error).__name__}: {error}") from error
    result = holder.get("result")
    if not isinstance(result, MicroResult):
        raise TypeError(f"{program.name} returned {type(result).__name__}, not a MicroResult")
    return result


def run(name: str, context: Mapping[str, Any] | None = None) -> MicroResult:
    """Run one registered program within its timeout_s; never raises; stamps elapsed_ms and counts the status.

    proves: an unknown name is refused, a raising program becomes status "error" with its exception named, an
        overrun becomes "unknown" with `timeout after Ns`, each with a next step; every result carries elapsed_ms
    does_not_prove: that the wrapped function's answer is right, or that an abandoned overrun thread ever ends
    closed_by: microprogram_test.py, which plants an unknown name, a raising program, a hung step and a
        self-stamped latency
    """
    started = time.perf_counter()
    program = REGISTRY.get(name)
    if program is None:
        refused = MicroResult(
            name,
            "",
            "refused",
            evidence_refs=(f"no program {name!r}; registered: {sorted(REGISTRY)}",),
            next="run `headron mind --micro list` and pass a registered name",
        )
        return _record(UNREGISTERED, refused, started, context=context)
    try:
        result = _bounded(program, context or {})
    except Exception as exc:  # noqa: BLE001 - the contract turns every raise into a declared status
        result = MicroResult(
            program.name,
            program.version,
            "error",
            evidence_refs=(f"{type(exc).__name__}: {exc}",),
            next=f"read the exception, fix its cause in {program.name}'s wrapped function, then rerun",
        )
    return _record(program.name, result, started, context=context)


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
    context: Mapping[str, Any] = {"files": args, "query": " ".join(args), "args": args}
    invalid_json = False
    if name in ("finance.evaluate", "data.reconcile", "compute.compose", "compute.contract"):
        try:
            if not args and name == "compute.contract":
                parsed = {}
            elif len(args) == 1:
                parsed = json.loads(args[0])
            else:
                raise ValueError("expected one JSON object")
            if not isinstance(parsed, dict):
                raise ValueError("expected a JSON object")
        except (ValueError, TypeError):
            invalid_json = True
            parsed = {}
        context = parsed
    if invalid_json:
        result = MicroResult(
            name,
            REGISTRY[name].version,
            "refused",
            evidence_refs=("expected one JSON object",),
            next="supply one JSON object",
        )
    else:
        result = run(name, context)
    if as_json:
        print(json.dumps(result.to_dict(), default=str))
    else:
        print(f"{result.program} {result.status}: {STATUSES[result.status]} ({result.elapsed_ms} ms)")
        print("\n".join(f"  {ref}" for ref in result.evidence_refs[:10]))
        if result.next:
            print(f"  next: {result.next}")
    return 0 if result.actionable else 1
