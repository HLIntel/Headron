#!/usr/bin/env python3
"""Planted cases: the microprogram contract refuses an undeclared status, never raises, and each wrapper
answers its own refusal with a declared status; every non-ok result names a next step, every step stops at
its timeout, and run() stamps latency and counts statuses."""

from __future__ import annotations

import contextlib
import io
import threading
import time
from types import ModuleType
from unittest import mock


def result_contract_cases(module: ModuleType) -> None:
    """A MicroResult is the contract itself: construction refuses what the contract does not declare."""
    import microprogram

    for status, confidence in (("maybe", None), ("OK", None), ("ok", 1.5)):
        bad = {"status": status, "confidence": confidence}
        try:
            microprogram.MicroResult("p", "1", status, confidence=confidence)
        except ValueError:
            continue
        raise SystemExit(
            f"FAIL micro result: {bad} was admitted; the contract declares {sorted(microprogram.STATUSES)}"
        )
    held = microprogram.MicroResult("p", "1", "ok", confidence=None, evidence_refs=["a.py"])  # pyright: ignore[reportArgumentType] - a list must be frozen
    if held.evidence_refs != ("a.py",) or not held.actionable:
        raise SystemExit(f"FAIL micro result: evidence {held.evidence_refs!r} not frozen, or ok not actionable")
    if any(
        microprogram.MicroResult("p", "1", status, next="x").actionable
        for status in set(microprogram.STATUSES) - {"ok"}
    ):
        raise SystemExit("FAIL micro result: a status other than ok reads actionable, so a refusal could be acted on")
    module.CASES.append(
        (
            "a MicroResult with an undeclared status or a confidence outside [0, 1] is refused at construction",
            "a status nobody declared, so a caller cannot tell a refusal from a pass",
        )
    )
    print("  ok    micro result refuses an undeclared status")


def run_never_raises_cases(module: ModuleType) -> None:
    """run() is the one door: an unknown name is refused and a raising program is status error, never an exception."""
    import microprogram

    missing = microprogram.run("no.such.program")
    if missing.status != "refused" or "no.such.program" not in missing.evidence_refs[0]:
        raise SystemExit(f"FAIL micro run: an unknown program answered {missing.to_dict()}")

    class Boom:
        name, version = "boom", "1"

        def run(self, context: object) -> microprogram.MicroResult:
            raise RuntimeError("planted")

    with mock.patch.dict(microprogram.REGISTRY, {"boom": Boom()}):
        try:
            raised = microprogram.run("boom")
        except RuntimeError as error:
            raise SystemExit(f"FAIL micro run: a raising program raised through run(): {error!r}") from None
    if raised.status != "error" or raised.evidence_refs != ("RuntimeError: planted",) or raised.output is not None:
        raise SystemExit(f"FAIL micro run: a raising program answered {raised.to_dict()}")
    module.CASES.append(
        (
            "run() refuses an unknown program and turns a raising one into status error naming the exception",
            "a step that raised through the caller, or an unknown name read as a KeyError crash",
        )
    )
    print("  ok    micro run never raises")


def wrapper_cases(module: ModuleType) -> None:
    """Each wrapper calls the existing function and maps its own failure to a declared status."""
    import graph
    import microprogram

    unclassified = microprogram.run("classify", {"files": []})
    classified = microprogram.run("classify", {"files": ["scripts/mind.py"]})
    if unclassified.status != "unknown" or classified.status != "ok" or classified.output["category"] == "unknown":
        raise SystemExit(f"FAIL micro classify: empty {unclassified.status}, mind.py {classified.to_dict()}")

    empty = microprogram.run("search", {"query": "  "})
    with mock.patch("mind.search", return_value=[{"path": "scripts/graph.py"}]) as search:
        found = microprogram.run("search", {"query": "edge domain"})
    if empty.status != "refused" or found.status != "ok" or found.evidence_refs != ("scripts/graph.py",):
        raise SystemExit(f"FAIL micro search: blank {empty.status}, query {found.to_dict()}")
    if search.call_args.args != ("edge domain",):
        raise SystemExit(f"FAIL micro search: mind.search was called with {search.call_args}")

    bad = graph.Graph()
    bad.add_node(graph.Node("claim:x", graph.NodeType.CLAIM))
    bad.add_node(graph.Node("f.py", graph.NodeType.FILE))
    bad.add_edge(graph.Edge("claim:x", "f.py", graph.EdgeType.RESTS_ON))
    bad.add_edge(graph.Edge("f.py", "gone", graph.EdgeType.RESTS_ON))
    refused = microprogram.run("graph.edges", {"graph": bad})
    clean = microprogram.run("graph.edges", {"graph": graph.Graph()})
    if refused.status != "refused" or len(refused.evidence_refs) != 2 or clean.status != "ok":
        raise SystemExit(f"FAIL micro graph.edges: planted {refused.to_dict()}, empty {clean.status}")
    if set(microprogram.REGISTRY) != {
        "classify",
        "search",
        "graph.edges",
        "context.credit",
        "task.obligations",
        "memory.validate",
        "ron.verify",
    }:
        raise SystemExit(f"FAIL micro registry: {sorted(microprogram.REGISTRY)} has a program no case here plants")
    module.CASES.append(
        (
            "classify, search and graph.edges map an unclassifiable change, a blank query and a bad edge to unknown, refused, refused",
            "a wrapper that reports ok over the wrapped function's own refusal",
        )
    )
    print("  ok    micro wrappers keep the wrapped refusal")


def cli_cases(module: ModuleType) -> None:
    """`headron mind --micro` exits 0 only for an actionable answer."""
    import mind

    codes = {}
    for name in ("list", "no.such.program"):
        with contextlib.redirect_stdout(io.StringIO()):
            codes[name] = mind.main(["--micro", name, "--json"])
    if codes != {"list": 0, "no.such.program": 1}:
        raise SystemExit(f"FAIL micro cli: exit codes {codes}")
    module.CASES.append(
        (
            "`headron mind --micro` exits 0 for list and 1 for a refused program",
            "a refusal that exits 0 to a caller reading only the code",
        )
    )
    print("  ok    micro cli fails closed")


def credit_cases(module: ModuleType) -> None:
    """context.credit scores each item by the verdict it changed, refuses an unpaired item, and reads an
    errored run as unknown, never as unsolved."""
    import json
    import os
    import tempfile
    from pathlib import Path

    import microprogram

    def runs(*solved: bool, error_seed: int | None = None) -> list[dict]:
        return [{"seed": s, "solved": v, "agent_error": s == error_seed} for s, v in enumerate(solved)]

    full = runs(True, True, False)
    without = {
        "helps.py": runs(False, False, False),
        "noise.py": runs(True, True, False),
        "hurts.py": runs(True, True, True),
    }
    scored = microprogram.run("context.credit", {"shape": "bugfix:py", "full": full, "without": without})
    credits = scored.output or {}
    want = {"helps.py": (2, 0, 2 / 3), "noise.py": (0, 0, 0.0), "hurts.py": (0, 1, -1 / 3)}
    got = {item: (row["helped"], row["hurt"], row["credit"]) for item, row in credits.items()}
    if scored.status != "ok" or got != want or credits["noise.py"]["p"] != 1.0:
        raise SystemExit(f"FAIL micro credit: planted helped/hurt/credit {want}, got {scored.status} {got}")
    if [round(microprogram.mcnemar_exact(*bc), 4) for bc in ((6, 0), (5, 0), (2, 2))] != [0.0312, 0.0625, 1.0]:
        raise SystemExit("FAIL micro credit: exact McNemar p is not 2*sum C(n,i)/2^n over the discordant pairs")

    # The trap: agentbench scores a timeout solved=False; read as a verdict it credits the removed item +1.
    outage = {"helps.py": runs(False, True, False, error_seed=0)}
    errored = microprogram.run("context.credit", {"shape": "bugfix:py", "full": full, "without": outage})
    if errored.status != "unknown" or errored.output is not None or "helps.py seed 0" not in errored.evidence_refs[0]:
        raise SystemExit(f"FAIL micro credit: an errored run answered {errored.to_dict()}, not unknown")
    for bad in ({"helps.py": runs(False, False)}, {"helps.py": [*runs(False, False, False), runs(True)[0]]}, {}):
        unpaired = microprogram.run("context.credit", {"shape": "bugfix:py", "full": full, "without": bad})
        if unpaired.status != "refused":
            raise SystemExit(f"FAIL micro credit: unpaired runs {bad} answered {unpaired.status}, not refused")

    with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HEADRON_HOME": home}):
        store = Path(home) / "context-credit.jsonl"
        context = {"shape": "bugfix:py", "full": full, "without": without, "record": True}
        microprogram.run("context.credit", context)
        first = store.read_bytes()
        microprogram.run("context.credit", context)
        lines = store.read_text(encoding="utf-8").splitlines()
        if len(lines) != 6 or not store.read_bytes().startswith(first) or json.loads(lines[0])["shape"] != "bugfix:py":
            raise SystemExit(f"FAIL micro credit: the log is not append-only, {len(lines)} lines after two records")
    module.CASES.append(
        (
            "context.credit scores helped/hurt per item, refuses an unpaired item, reads an errored run as unknown, appends only",
            "an outage credited to the removed item, or a credit log rewritten over earlier measurements",
        )
    )
    print("  ok    micro context.credit scores the verdict an item changed")


def obligation_cases(module: ModuleType) -> None:
    """task.obligations is ok only when every obligation is proven on the tree read; stale evidence is unknown, an
    open one is refused with its procedure, and the ledger outlives the process that wrote it."""
    import json
    import os
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    import microprogram
    import obligations

    def ask(tree: str) -> microprogram.MicroResult:
        return microprogram.run("task.obligations", {"task": "lane-a", "tree": tree})

    with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HEADRON_HOME": home}):
        if ask("t1").status != "unknown":
            raise SystemExit("FAIL micro obligations: an empty ledger answered something other than unknown")
        for statement, check in (("tests pass", ""), ("", "pytest")):
            try:
                obligations.add("lane-a", "tests", statement, check)
            except obligations.LedgerError:
                continue
            raise SystemExit(
                f"FAIL micro obligations: recorded an obligation with statement={statement!r} check={check!r}"
            )
        obligations.add("lane-a", "tests", "the suite passes", "headron verify")
        obligations.add("lane-a", "docs", "README names the ledger", "grep -q obligations README.md")
        try:
            obligations.close("lane-a", "tests", "", at="t1")
            raise SystemExit("FAIL micro obligations: a done claim with no evidence was recorded as proven")
        except obligations.LedgerError:
            pass
        for nowhere in (obligations.UNKNOWN_TREE, "t1+dirty"):
            try:
                obligations.close("lane-a", "tests", "receipt:abc", at=nowhere)
                raise SystemExit(f"FAIL micro obligations: evidence on {nowhere} was recorded as proven")
            except obligations.LedgerError:
                pass
        if obligations.tree(Path(home)) != obligations.UNKNOWN_TREE:
            raise SystemExit("FAIL micro obligations: a directory outside any git tree named a tree")
        here = Path.cwd()
        try:
            os.chdir(home)  # the default root is the repo the task is in, not Headron's checkout
            if obligations.tree() != obligations.UNKNOWN_TREE:
                raise SystemExit("FAIL micro obligations: tree() outside any git tree read another repo's tree")
        finally:
            os.chdir(here)
        legacy = {"state": "proven", "tree": obligations.UNKNOWN_TREE}  # a row written before close refused it
        if obligations.standing(legacy, obligations.UNKNOWN_TREE) != "unknown":
            raise SystemExit("FAIL micro obligations: evidence on an unknown tree read proven on an unknown tree")
        obligations.close("lane-a", "tests", "receipt:abc", at="t1")
        opened = ask("t1")
        if opened.status != "refused" or "docs" not in (opened.next or "") or "grep -q" not in (opened.next or ""):
            raise SystemExit(
                f"FAIL micro obligations: an open obligation answered {opened.to_dict()}, not refused with its check"
            )
        obligations.close("lane-a", "docs", "commit:def", at="t1")
        if ask("t1").status != "ok":
            raise SystemExit("FAIL micro obligations: every obligation proven on t1 did not answer ok on t1")
        for stale in ("t2", "t1+dirty", obligations.UNKNOWN_TREE):
            if ask(stale).status != "unknown":
                raise SystemExit(
                    f"FAIL micro obligations: evidence for t1 answered {ask(stale).status} on {stale}, not unknown"
                )
        # SURVIVES COMPACTION: a fresh process, which shares no memory with this one, reads the same state.
        fresh = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json, obligations; print(json.dumps(obligations.report('lane-a', 't1')[0]))",
            ],
            cwd=Path(obligations.__file__).parent,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if fresh.returncode or json.loads(fresh.stdout or "null") != "ok":
            raise SystemExit(f"FAIL micro obligations: a fresh process read {fresh.stdout!r} {fresh.stderr[-300:]!r}")
        store = obligations.path("lane-a")
        store.write_text(store.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
        if ask("t1").status != "unknown":
            raise SystemExit("FAIL micro obligations: a corrupt ledger line was skipped, not refused")
    module.CASES.append(
        (
            "task.obligations is ok only when all are proven on this tree; stale is unknown, open is refused, corrupt is unknown",
            "a task called done on evidence for another tree, an obligation with no procedure, or a dropped ledger line",
        )
    )
    print("  ok    micro task.obligations binds done to evidence on this tree")


def memory_cases(module: ModuleType) -> None:
    """memory.validate serves a claim only while it can be shown to hold: a changed scope, an unreadable commit,
    broken evidence, a reported-only label or a corrupt record is unknown; a refuted claim is refused."""
    import subprocess
    import tempfile
    from pathlib import Path

    import microprogram

    def git(root: Path, *argv: str) -> str:
        done = subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True, timeout=60, check=True)
        return done.stdout.strip()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git(root, "init", "-q")
        (root / "gate.py").write_text("RULE = 1\n", encoding="utf-8")
        (root / "other.py").write_text("x = 1\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seed")
        sha = git(root, "rev-parse", "HEAD")
        base = {
            "statement": "the gate holds RULE",
            "label": "CONFIRMED",
            "evidence": ["file:gate.py"],
            "provenance": "planted",
            "status": "holds",
        }
        registry = {
            "fresh": {**base, "validity": {"source_commit": sha, "scope": ["gate.py"]}},
            "rules": {**base, "validity": {"source_commit": sha, "scope": ["rules"]}},
            "bare": dict(base),
            "unborn": {**base, "validity": {"source_commit": "0" * 40, "scope": ["gate.py"]}},
            "reported": {**base, "label": "REPORTED"},
            "gone": {**base, "evidence": ["file:missing.py"]},
            "corrupt": {"statement": "no label or status"},
            "old": {**base, "status": "refuted", "superseded_by": "fresh"},
        }

        def ask(claim: str) -> microprogram.MicroResult:
            return microprogram.run("memory.validate", {"claim": claim, "claims": registry, "root": root})

        for claim in ("fresh", "bare"):
            if ask(claim).status != "ok" or (ask(claim).output or {}).get("label") != "CONFIRMED":
                raise SystemExit(f"FAIL micro memory: a holding claim {claim} answered {ask(claim).to_dict()}")
        (root / "other.py").write_text("x = 2\n", encoding="utf-8")
        if ask("fresh").status != "ok":
            raise SystemExit("FAIL micro memory: a change outside the claim's scope made it stale")
        if ask("rules").status != "ok":
            raise SystemExit(f"FAIL micro memory: an unchanged scope answered {ask('rules').to_dict()}")
        (root / "rules").mkdir()
        (root / "rules" / "new.py").write_text("NEW = 1\n", encoding="utf-8")  # untracked: git diff never sees it
        if ask("rules").status != "unknown":
            raise SystemExit("FAIL micro memory: a file created in the claim's scope since its commit left it ok")
        (root / "gate.py").write_text("RULE = 2\n", encoding="utf-8")
        for claim, want in (
            ("fresh", "unknown"),
            ("unborn", "unknown"),
            ("reported", "unknown"),
            ("gone", "unknown"),
            ("corrupt", "unknown"),
            ("old", "refused"),
            ("nobody", "refused"),
        ):
            got = ask(claim)
            if got.status != want:
                raise SystemExit(
                    f"FAIL micro memory: claim {claim} answered {got.status}, not {want}: {got.evidence_refs}"
                )
        if "changed since" not in ask("fresh").evidence_refs[1] or "fresh" not in (ask("old").next or ""):
            raise SystemExit("FAIL micro memory: a stale or refuted claim did not say why and what to serve instead")
    module.CASES.append(
        (
            "memory.validate is ok only while a claim holds and its scope is unchanged; stale, reported, corrupt is unknown",
            "a remembered fact served after the code it describes changed, or a refuted claim served at all",
        )
    )
    print("  ok    micro memory.validate serves a claim only while it holds")


def next_step_cases(module: ModuleType) -> None:
    """Every result that may not be acted on says what to try next, from the constructor to each wrapper."""
    import microprogram

    for status in sorted(set(microprogram.STATUSES) - {"ok"}):
        for blank in (None, "", "   "):
            try:
                microprogram.MicroResult("p", "1", status, next=blank)
            except ValueError:
                continue
            raise SystemExit(f"FAIL micro next: a {status} result with next={blank!r} was admitted, a dead end")

    class Mute:
        name, version = "mute", "1"

        def run(self, context: object) -> microprogram.MicroResult:
            return microprogram.MicroResult(self.name, self.version, "refused", evidence_refs=("planted",))

    with mock.patch.dict(microprogram.REGISTRY, {"mute": Mute()}):
        mute = microprogram.run("mute")
    if mute.status != "error" or not mute.evidence_refs[0].startswith("ValueError: status 'refused' names no next"):
        raise SystemExit(f"FAIL micro next: a program refusing with no next step answered {mute.to_dict()}")
    answers = [
        microprogram.run("no.such.program"),
        microprogram.run("classify", {"files": []}),
        microprogram.run("search", {"query": " "}),
        mute,
    ]
    if any(not (answer.next or "").strip() for answer in answers):
        raise SystemExit(f"FAIL micro next: a non-ok answer names no next step: {[a.to_dict() for a in answers]}")
    module.CASES.append(
        (
            "a non-ok MicroResult with no next step is refused at construction, and every non-ok answer names one",
            "a refusal that does not say what to try next, so the caller stops at a dead end",
        )
    )
    print("  ok    micro non-ok results name a next step")


def timeout_cases(module: ModuleType) -> None:
    """A step that overruns its timeout_s is answered unknown with `timeout after Ns`, not waited on."""
    import microprogram

    release = threading.Event()

    class Hung:
        name, version, timeout_s = "hung", "1", 0.05

        def run(self, context: object) -> microprogram.MicroResult:
            release.wait(2)  # bounded, so a mutant without the timeout still finishes and is judged
            return microprogram.MicroResult(self.name, self.version, "ok")

    started = time.perf_counter()
    try:
        with mock.patch.dict(microprogram.REGISTRY, {"hung": Hung()}):
            hung = microprogram.run("hung")
        waited = time.perf_counter() - started
    finally:
        release.set()
    if hung.status != "unknown" or hung.evidence_refs != ("timeout after 0.05s",) or not hung.next or waited > 1.0:
        raise SystemExit(f"FAIL micro timeout: a hung step answered {hung.to_dict()} after {waited:.2f}s")
    if any(getattr(program, "timeout_s", 0) <= 0 for program in microprogram.REGISTRY.values()):
        raise SystemExit("FAIL micro timeout: a registered program declares no positive timeout_s")
    module.CASES.append(
        (
            "a step that overruns its timeout_s answers unknown with `timeout after Ns` and a next step",
            "a hung step that holds the caller forever, or an overrun read as ok",
        )
    )
    print("  ok    micro run stops a hung step at its timeout")


def elapsed_cases(module: ModuleType) -> None:
    """run() stamps elapsed_ms on every answer; a program's own value is replaced, never trusted."""
    import microprogram

    class Liar:
        name, version = "liar", "1"

        def run(self, context: object) -> microprogram.MicroResult:
            threading.Event().wait(0.02)  # a measurable latency to stamp
            return microprogram.MicroResult(self.name, self.version, "ok", elapsed_ms=-1.0)

    with mock.patch.dict(microprogram.REGISTRY, {"liar": Liar()}):
        liar = microprogram.run("liar")
    missing = microprogram.run("no.such.program")
    if liar.elapsed_ms is None or not 15.0 <= liar.elapsed_ms < 1000.0 or missing.elapsed_ms is None:
        raise SystemExit(f"FAIL micro elapsed: run() left latency {liar.elapsed_ms!r} and {missing.elapsed_ms!r}")
    if liar.to_dict().get("elapsed_ms") != liar.elapsed_ms:
        raise SystemExit(f"FAIL micro elapsed: to_dict() drops the latency: {liar.to_dict()}")
    module.CASES.append(
        (
            "run() stamps elapsed_ms on every answer and replaces a latency the program set itself",
            "a step's latency the program reported for itself, or none at all",
        )
    )
    print("  ok    micro run stamps latency")


def stats_cases(module: ModuleType) -> None:
    """run() counts each program's statuses, and `headron mind --health` prints them."""
    import microprogram
    import mind

    class Flip:
        name, version = "flip", "1"

        def run(self, context: object) -> microprogram.MicroResult:
            if context.get("refuse"):  # pyright: ignore[reportAttributeAccessIssue] - a Mapping at run time
                return microprogram.MicroResult(self.name, self.version, "refused", next="planted")
            return microprogram.MicroResult(self.name, self.version, "ok")

    before = microprogram.stats().get("flip", {}).get("counts", {})
    with mock.patch.dict(microprogram.REGISTRY, {"flip": Flip()}):
        for refuse in (False, True, True):
            microprogram.run("flip", {"refuse": refuse})
    row = microprogram.stats().get("flip", {})
    after = row.get("counts", {})
    delta = {status: after.get(status, 0) - before.get(status, 0) for status in microprogram.STATUSES}
    if delta != {"ok": 1, "unknown": 0, "refused": 2, "error": 0} or row.get("max_ms", -1) < 0:
        raise SystemExit(f"FAIL micro stats: three planted runs counted {delta}, row {row}")
    with mock.patch.object(mind, "gather_receipts", return_value=[]):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            mind.main(["--health"])
    if "micro flip: ok=" not in out.getvalue() or "refused=" not in out.getvalue():
        raise SystemExit(f"FAIL micro stats: `mind --health` does not print the counters: {out.getvalue()!r}")
    module.CASES.append(
        (
            "run() counts each program's statuses and latency, and `headron mind --health` prints them",
            "a step that keeps refusing or slowing down with no counter to show it",
        )
    )
    print("  ok    micro run counts statuses per program")


def ron_cases(module: ModuleType) -> None:
    """ron.verify is ok only for an intact bundle whose obligations are all proven on the tree read: a finding or
    an open obligation is refused, evidence on another tree is unknown, and no bundle named is refused."""
    import os
    import shutil
    import tempfile
    from pathlib import Path

    import microprogram
    import obligations
    import ronbundle

    def ask(bundle: Path | str, tree: str = "") -> microprogram.MicroResult:
        return microprogram.run("ron.verify", {"bundle": str(bundle), "tree": tree})

    with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HEADRON_HOME": home}):
        top = Path(home)
        log = top / "pytest.log"
        log.write_text("3 passed\n", encoding="utf-8")
        obligations.add("lane-done", "tests", "the suite passes", "pytest")
        obligations.close("lane-done", "tests", "evidence/pytest.log", at="t1")
        obligations.add("lane-open", "docs", "the docs say so", "headron check")
        done, open_bundle, edited = top / "done.ron", top / "open.ron", top / "edited.ron"
        packs = [
            ronbundle.pack("lane-done", done, [], [log], at="t1"),
            ronbundle.pack("lane-open", open_bundle, [], [], at="t1"),
        ]
        shutil.copytree(done, edited)
        (edited / "evidence" / "pytest.log").write_text("0 passed\n", encoding="utf-8")
        said = {
            "done": ask(done),
            "done on t1": ask(done, "t1"),
            "stale": ask(done, "t2"),
            "dirty": ask(done, "t1+dirty"),
            "open": ask(open_bundle),
            "edited": ask(edited),
            "missing": ask(top / "nowhere.ron"),
            "none": ask(""),
        }
    want = {
        "done": "ok",
        "done on t1": "ok",
        "stale": "unknown",
        "dirty": "unknown",
        "open": "refused",
        "edited": "refused",
        "missing": "refused",
        "none": "refused",
    }
    got = {key: result.status for key, result in said.items()}
    if any(packs) or got != want or "docs" not in (said["open"].next or ""):
        raise SystemExit(f"FAIL micro ron.verify: packs {packs}, answered {got}, want {want}")
    module.CASES.append(
        (
            "ron.verify is ok only for an intact bundle proven on this tree; a finding or open obligation is refused, "
            "another tree is unknown",
            "a bundle read as done with an edited file, an open obligation, or evidence for another tree",
        )
    )
    print("  ok    micro ron.verify binds done to an intact bundle proven on this tree")


def run(module: ModuleType) -> None:
    for cases in (
        result_contract_cases,
        run_never_raises_cases,
        wrapper_cases,
        cli_cases,
        next_step_cases,
        timeout_cases,
        elapsed_cases,
        stats_cases,
        credit_cases,
        obligation_cases,
        memory_cases,
        ron_cases,
    ):
        cases(module)
