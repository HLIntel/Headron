"""Knowledge commands and hooks.

The `headron` commands, hooks and generated blocks that answer from the knowledge records. Split
from knowledge.py (Core compaction step 2b) so the records library imports no command module:
everything here that reaches atlas, port, agents, agentpolicy, verify, agreement or contextcost does
so lazily, and knowledge.py itself stays out of the import cycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from atlascore import ROOT, atlas, git_run, resolved_once, route_targets, text_of
from boundedinput import read_stdin
from knowledge import (
    RECURRING,
    TIERS,
    _hook_answer,
    draft,
    failures,
    failures_matching,
    proof_flow_block,
    role,
    settings_block,
    success_kind_errors,
    successes,
)

if TYPE_CHECKING:
    from agentpolicy import Verdict


def success_wiring_errors() -> list[str]:
    """successes_answer_recurring_failures — the ledger is a graph: failure -> move -> guard (3.43.0).

    A failure record teaches what to avoid; seen twice, it has proven that avoiding is not enough and
    the replacing MOVE must be written down where an agent reads it. Each success carries the ATS fields an
    agent reuses as a step (move, when, verification), names the failures it answers, and names functions
    in this tree that prove it — so a success cannot be a slogan, and a pairing cannot dangle.
    """
    from agentpolicy import _resolves  # noqa: PLC0415

    failures = atlas().get("agent_failure_modes") or {}
    successes = atlas().get("agent_success_patterns") or {}
    errors: list[str] = []
    if not successes:
        return [
            "atlas.yaml declares no agent_success_patterns, so a failure says what went wrong and nothing says what to do"
        ]
    for name, spec in successes.items():
        spec = spec or {}
        errors += [
            f"agent_success_patterns/{name} has no `{f}`"
            for f in ("move", "when", "verification", "pairs", "proven_by")
            if not spec.get(f)
        ]
        errors += [
            f"agent_success_patterns/{name} pairs '{p}', which agent_failure_modes does not hold"
            for p in spec.get("pairs") or []
            if p not in failures
        ]
        errors += [
            f"agent_success_patterns/{name} is proven_by {r}, which is not in this tree"
            for r in (str(r) for r in spec.get("proven_by") or [])
            if not _resolves(r)
        ]
    errors += success_kind_errors(failures, successes)
    answered = {p for s in successes.values() for p in (s or {}).get("pairs") or []}
    errors += [
        f"agent_failure_modes/{name} is sighted {int((spec or {}).get('sightings') or 0)} times and no success "
        "names the move that replaces it — add one to agent_success_patterns with `pairs` naming it"
        for name, spec in failures.items()
        if int((spec or {}).get("sightings") or 0) >= RECURRING and name not in answered
    ]
    return errors


def gate_example_block() -> str:
    """A real `gate` answer for a real file in this tree, regenerated every build, so the example the
    landing page shows is the command's output today and never a transcript that aged."""
    import shlex  # noqa: PLC0415

    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415

    path = "scripts/doctor.py"
    rows = [gate_record(path, g) for g in required_gates({"change_class": "source_change"})]
    body = [
        f"{n}. {r['gate']}: " + (shlex.join(r["argv"]) if r["argv"] else f"{r['state']} — {r['why']}")
        for n, r in enumerate(rows, 1)
    ]
    return "```console\n$ headron gate " + path + "\n" + "\n".join(body) + "\n```"


def port_example_block() -> str:
    """The socket, drawn live: one file, one place and the tree, each as the glyph line `port` prints (3.46.0)."""
    import port  # noqa: PLC0415

    rows = [
        (t, port.line(port.record(t, None, "codebase", None, resolved_once(ROOT)), color=False))
        for t in ("scripts/doctor.py", "scripts", ".")
    ]
    return "```console\n" + "\n".join(f"$ headron port {t} --line\n{ln}" for t, ln in rows) + "\n```"


def glance_figures() -> dict:
    """The headline figures as data (3.54.0): docs/INDEX.md renders them and `.agent/facts.json` carries them."""
    from contextcost import footprint  # noqa: PLC0415

    a = atlas()
    return {
        "languages": len(route_targets()),
        "extensions": len(a.get("artifact_routes") or {}),
        "gates": len(a.get("gate_tools") or {}),
        "runtimes": len(a.get("runtime_entry") or []),
        "failures": len(a.get("agent_failure_modes") or {}),
        "successes": len(a.get("agent_success_patterns") or {}),
        "invariants": len(a.get("hard_invariants") or []),
        "instruments": len(a.get("instruments") or {}),
        "edges": _edges(),
        "deps": footprint()["dependencies"],
    }


def glance_block() -> str:
    """The headline figures, computed on every build: what a reader should know in one line (3.13.0)."""
    g = glance_figures()
    return (
        f"**{g['languages']}** languages · **{g['extensions']}** extensions · "
        f"**{g['gates']}** gates · **{g['runtimes']}** runtimes · "
        f"**{g['failures']}** failure shapes · **{g['successes']}** success moves · "
        f"**{g['invariants']}** invariants · **{g['instruments']}** instruments · "
        f"**{g['edges']}** agreement edges · **{g['deps']}** dependency"
    )


def _edges() -> int:
    """How many declarations resolve to a file that implements them — the agreement graph's size.

    ON THE LANDING PAGE BECAUSE IT IS THE ONE FIGURE THAT SAYS WHETHER THE REST ARE BACKED. 42
    invariants and 63 instruments are claims; an edge is a claim with a file behind it. The number
    is GENERATED, and `agreement_errors` fails the build when any declaration resolves to none — so
    an edge count that stops rising beside a roster that keeps growing is visible rather than quiet.
    """
    from agreement import index  # noqa: PLC0415

    return sum(len(rows) for rows in index().values())


README_BLOCKS = {"gate-example": gate_example_block, "port-example": port_example_block, "proof-flow": proof_flow_block}


ELSEWHERE_BLOCKS = {"settings": ("models/README.md", settings_block), "glance": ("docs/INDEX.md", glance_block)}


def steps(path_value: str, runtime: str, change: str, as_json: bool, tier: str = "mid") -> int:
    """`headron steps <path> --runtime <id>` — the ordered implementation plan for ONE runtime (3.14.0).

    `plan` answers which gates; this answers what to do, in order, from where this runtime stands: how it
    reaches Headron, what to load, the commands that prove the change, the budget, the sandbox an autonomous
    run needs, the done check, and where the work RETURNS — a pull request for an agent, a checklist and
    a pasted ledger entry for a chat. Every line is read from a declaration; nothing here is typed per runtime."""
    import json as _json

    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415
    from atlascore import route_for  # noqa: PLC0415
    from runtime import resolve  # noqa: PLC0415

    a = atlas()
    entry = {str(e["id"]): e for e in a.get("runtime_entry") or []}
    runtime = (runtime or "").strip() or resolve()["runtime"]
    if runtime not in entry:
        print(f"unknown runtime '{runtime}' — set --runtime to one of: {', '.join(sorted(entry))}")
        return 2
    route = route_for(path_value)
    via = ((a.get("native_agent_tools") or {}).get("runtimes") or {}).get(runtime, {}).get("headron_via") or []
    runs = bool(via)
    gates = [gate_record(path_value, g) for g in required_gates({"change_class": change})] if route else []
    budget = (a.get("agent_policy") or {}).get("default_budgets") or {}
    plan = [
        f"reach Headron through {', '.join(via) or 'the page itself: ' + str(entry[runtime]['loads'])}",
        f"route {path_value}: "
        + (f"pack {route} — load languages/{route}/ only" if route else "no route; refuse, do not guess"),
        *[
            f"prove with {g['gate']}: "
            + (__import__("shlex").join(g["argv"]) if g["argv"] else f"{g['state']} — {g['why']}")
            for g in gates
        ],
        f"stay inside the budget: {', '.join(f'{k} {v}' for k, v in budget.items())}",
    ]
    process = (a.get("processes") or {}).get("implementation") or {}
    plan += [
        f"stop when: {', '.join(process.get('stop_when') or [])} — escalate when: {', '.join(process.get('escalate_when') or [])}",
        f"accepted only with: {process.get('returns', 'every gate result, including those NOT RUN')}",
    ]
    plan += (
        [
            "autonomous? isolate it: python scripts/sandboxgen.py docker <contract>",
            "done only when: python scripts/verify.py exits 0",
            "return: python scripts/branchstate.py --land — a pull request, never a bare push",
        ]
        if runs
        else [
            "return: the gate checklist above with each claim labelled; file any gap in Headron as a pasted ledger entry (skills/headron/SKILL.md)"
        ]
    )
    plan += TIERS.get(tier, [])
    if tier == "frontier":
        plan = [s for s in plan if s.startswith(("prove with", "route", "return", "done only"))]
    if as_json:
        print(
            _json.dumps(
                {
                    "schema": 1,
                    "command": "steps",
                    "runtime": runtime,
                    "tier": tier,
                    "path": path_value,
                    "route": route,
                    "change_class": change,
                    "steps": plan,
                },
                indent=2,
            )
        )
    else:
        print("\n".join(f"{n}. {s}" for n, s in enumerate(plan, 1)))
    return 0 if route else 2


def resume(as_json: bool) -> int:
    """`headron resume` — where interrupted work stands and the one next action, rebuilt from state, never memory.

    A role switch, a killed session or a new agent picking up a lane all start here: the lane (ahead,
    behind, uncommitted), a plant a killed run left, the last audit event, and the last verify record."""
    import json as _json

    from safeedit import _git_path, plant_leftovers  # noqa: PLC0415

    def git(*args: str) -> str:
        return git_run(ROOT, *args).stdout.strip()

    branch = git("branch", "--show-current")
    counts = git("rev-list", "--left-right", "--count", "@{upstream}...HEAD").split() or ["?", "?"]
    dirty = len([ln for ln in git("status", "--porcelain").splitlines() if ln])
    last_verify = _git_path("headron-last-verify.json")
    verdict = _json.loads(text_of(last_verify)) if last_verify.is_file() else None
    from verify import input_digest  # noqa: PLC0415

    current_verdict = bool(verdict and verdict.get("input_digest") == input_digest())
    audits = sorted((ROOT / ".agent" / "audit").glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    last_event = (text_of(audits[-1]).splitlines() or [""])[-1] if audits else ""
    leftovers = plant_leftovers()
    from hostshape import JOURNAL, read_journal, unverified_steps  # noqa: PLC0415

    journal_entries, journal_findings = read_journal(_git_path(JOURNAL).parent)
    partial = unverified_steps(journal_entries)
    lessons_file = _git_path("headron-lessons.json")
    recurring = [k for k, n in (_json.loads(text_of(lessons_file)) if lessons_file.is_file() else {}).items() if n >= 2]
    failed = (
        [r["id"] for r in (verdict or {}).get("rows", []) if r["verdict"] not in ("PASS", "REUSED")]
        if current_verdict
        else []
    )
    nxt = (
        f"repair the journal — {journal_findings[0]}"
        if journal_findings
        else "run `python scripts/atlas_test.py --restore` — a killed run left a plant"
        if leftovers
        else f"re-verify step {partial[-1]} — begun and never verified, so its write may be partial"
        if partial
        else f"fix {failed[0]}, then `headron verify`"
        if failed
        else "`headron verify` — the last verification did not pass"
        if current_verdict and (verdict or {}).get("exit") != 0
        else "`headron verify` — nothing has proven this tree yet"
        if (dirty or counts[1] not in ("0", "?")) and not current_verdict
        else "commit, then `python scripts/branchstate.py --land`"
        if dirty or counts[1] not in ("0", "?")
        else "start a task: `headron steps <file> --runtime <id>` under the role the user named"
    )
    state = {
        "schema": 1,
        "command": "resume",
        "branch": branch,
        "behind": counts[0],
        "ahead": counts[1],
        "uncommitted": dirty,
        "plant_leftovers": len(leftovers),
        "unverified_steps": partial,
        "last_verify_exit": (verdict or {}).get("exit"),
        "failing_gates": failed,
        "recurring_failures": recurring[:3],
        "last_audit_event": _json.loads(last_event).get("event") if last_event else None,
        "next": nxt,
    }
    print(
        _json.dumps(state, indent=2)
        if as_json
        else "\n".join(f"{k:>18}: {v}" for k, v in state.items() if k not in ("schema", "command"))
    )
    return 1 if journal_findings else 0


COMMANDS = {
    "steps": lambda a: steps(a.path, a.runtime, a.change, a.json, a.tier),
    "failures": lambda a: (
        draft(a.id or "", a.draft, a.json)
        if a.draft
        else __import__("agents").failures_shown(a.shown, a.route, atlas().get("agent_failure_modes") or {})
        if a.shown
        else failures_matching(a.match, a.json)
        if a.match
        else failures(a.id, a.json, a.for_, a.limit)
    ),
    "successes": lambda a: successes(a.id, a.json, a.for_, a.limit),
    "role": lambda a: role(a.name, a.json),
    "revise": lambda a: __import__("claims").main(
        [*([a.claim] if a.claim else []), *(["--on", a.on] if a.on else []), *(["--json"] if a.json else [])]
    ),
    "propose": lambda a: __import__("propose").main(
        [*(["--check", a.check] if a.check else []), *(["--json"] if a.json else [])]
    ),
    "judge": lambda a: __import__("judge").main(
        [
            *([a.id] if a.id else []),
            *([a.answer] if a.answer else []),
            *([a.p] if a.p else []),
            *[x for f in a.fact for x in ("--fact", f)],
            *(["--calibrate", a.calibrate] if a.calibrate else []),
            *(["--state", a.state] if a.state is not None else []),
            *(["--to", a.to] if a.to else []),
        ]
    ),
    "model": lambda a: __import__("model").main([*(["--to", a.to] if a.to else []), *(["--json"] if a.json else [])]),
    "links": lambda a: __import__("links").main(["--json"] if a.json else []),
    "resume": lambda a: resume(a.json),
    "shell": lambda a: shell_hook(read_stdin()) if a.hook else shell_check(" ".join(a.cmd), a.json),
    "brainstorm": lambda a: __import__("brainstorm").main(
        [*(["--new"] if a.new else []), *a.record, *(["--json"] if a.json else [])]
    ),
    "inspect": lambda a: __import__("artifacts").cli(a.files, a.json),
    "task": lambda a: __import__("taskimage").cli(a.action, a.target, a.execute, a.json),
    "data": lambda a: __import__("datakit").cli(a.action, a.files, a.schema, a.source, a.limit, a.json, a.formula),
    "port": lambda a: (
        edit_guard_hook(read_stdin())
        if a.guard
        else port_hook(read_stdin())
        if a.hook
        else __import__("port").main(
            [
                a.target,
                *(["--lens", a.lens] if a.lens else []),
                "--frame",
                a.frame,
                *(["--runtime", a.runtime] if a.runtime else []),
                *[f for f, on in (("--json", a.json), ("--line", a.line)) if on],
            ]
        )
    ),
    "landed": lambda a: __import__("branchstate").landed(a.branch, a.base),
    "md": lambda a: __import__("mdshape").main(
        [*([a.repo] if a.repo else []), *(["--staged"] if a.staged else []), *(["--base", a.base] if a.base else [])]
    ),
    "delegate": lambda a: __import__("delegate").main(
        [*(["--task", a.task] if a.task else []), *(["--json"] if a.json else [])]
    ),
    "handoff": lambda a: __import__("handoff").main(
        [a.path, *(["--task", a.task] if a.task else []), "--change", a.change, *(["--json"] if a.json else [])]
    ),
    "cadence": lambda a: __import__("cadence").main(
        [*(["--minutes", str(a.minutes)] if a.minutes else []), *(["--json"] if a.json else [])]
    ),
    "schedtargets": lambda a: __import__("schedtargets").main(
        [*(["--root", a.root] if a.root else []), *(["--platform", a.platform] if a.platform else [])]
    ),
    "intake": lambda a: __import__("intake").main(
        [*a.prompt, *(["--json"] if a.json else []), *(["--brief"] if a.brief else [])]
    ),
    "mind": lambda a: __import__("mind").main(
        [
            *(["--classify"] if a.classify else []),
            *([f"--search={a.search}"] if getattr(a, "search", None) else []),
            *([f"--micro={a.micro}"] if getattr(a, "micro", None) else []),
            *(["--plan"] if a.plan else []),
            *(["--route"] if a.route else []),
            *(["--direct"] if getattr(a, "direct", False) else []),
            *(["--health"] if a.health else []),
            *(["--receipts"] if getattr(a, "receipts", False) else []),
            *(["--limit", str(a.limit)] if a.limit is not None else []),
            *(a.files if getattr(a, "files", None) else []),
            *(["--json"] if a.json else []),
        ]
    ),
    "find": lambda a: __import__("atlasindex").find_main(
        [
            *(["--limit", str(a.limit)] if a.limit else []),
            *(["--exact"] if a.exact else []),
            *(["--snippet"] if a.snippet else []),
            *(["--line"] if a.line else []),
            *(["--json"] if a.json else []),
            *([f"--tier={a.tier}"] if a.tier else []),
            *([f"--shard={a.shard}"] if a.shard else []),
            *([f"--path={a.path}"] if a.path else []),
            *([f"--exclude={a.exclude}"] if a.exclude else []),
            *a.query,
        ]
    ),
    "sweep": lambda a: __import__("sweep").main(
        [*(["--line"] if a.line else []), *(["--json"] if a.json else []), *([a.target] if a.target else [])]
    ),
    "polyglot": lambda a: __import__("polyglot").main(
        [
            *([a.path] if getattr(a, "path", None) else []),
            *(["--capabilities"] if getattr(a, "capabilities", False) else []),
            *(["--boundaries"] if getattr(a, "boundaries", False) else []),
            *(["--plan", str(a.plan)] if getattr(a, "plan", None) is not None else []),
            *(["--explain", str(a.explain)] if getattr(a, "explain", None) is not None else []),
            *(["--json"] if getattr(a, "json", False) else []),
        ]
    ),
    "ask": lambda a: __import__("help_dispatch").main(
        [
            *([a.query] if getattr(a, "query", None) else []),
            *(["--root", a.root] if getattr(a, "root", None) else []),
            *(["--plan", a.plan] if getattr(a, "plan", None) else []),
            *(["--runtime", a.runtime] if getattr(a, "runtime", None) else []),
            *(["--json"] if getattr(a, "json", False) else []),
        ]
    ),
}


def shell_check(command: str, as_json: bool) -> int:
    """`headron shell "<cmd>"` — the decider a runtime's own PreToolUse hook calls before running a command.

    WHY A COMMAND AND NOT ONLY A FUNCTION (3.27.0). Five standing verdicts in the ledger shared one reason:
    the shell belongs to the agent, so no FILE here can refuse it. A function fixes half of that and a
    COMMAND fixes the rest — every runtime can already run one, so the closer is the same in Claude Code,
    Codex, opencode or a bare shell, and it is plug-and-play: no import, no framework, one exit code.
    Exit 0 allows, 3 refuses. It FAILS OPEN on anything it cannot parse, because a guard that blocks
    correct commands gets switched off.
    """
    import json as _json

    from agentpolicy import shell_verdict  # noqa: PLC0415

    verdict = shell_verdict(command)
    _field_refusal(verdict, command)
    if as_json:
        print(
            _json.dumps(
                {
                    "schema": 1,
                    "command": "shell",
                    "allowed": verdict.allowed,
                    "control": verdict.control,
                    "why": verdict.reason,
                },
                indent=2,
            )
        )
    else:
        print(("ALLOW  " if verdict.allowed else "REFUSE ") + verdict.reason)
    return 0 if verdict.allowed else 3


def _field_refusal(verdict: Verdict, command: str) -> None:
    """A refusal onto the field ledger: the shape that fired and the command's digest, never its text.

    The shape id is what makes a refusal → resolution join possible: the same shape firing again in the
    same session is a re-fire; silence after it is the shape resolved.
    """
    if verdict.allowed:
        return
    import agentaudit  # noqa: PLC0415
    import agents  # noqa: PLC0415

    shape = agentaudit.digest(verdict.reason)["sha256"][:12]  # a shape's reason is fixed text: its hash is its id
    agents.field("field_refused", {"shape": shape, "control": verdict.control, "command": agentaudit.digest(command)})


def hook_input(text: str) -> dict:
    """The `tool_input` of a runtime hook's stdin record (Claude Code and Codex share the shape), or {}.

    {} on anything unreadable: a hook that crashes on a record it did not expect gets switched off.
    """
    import json as _json

    try:
        record = _json.loads(text)
    except ValueError:
        return {}
    if isinstance(record, dict):
        _hook_beat(record)
    tool_input = record.get("tool_input") if isinstance(record, dict) else None
    return tool_input if isinstance(tool_input, dict) else {}


def _hook_beat(record: dict) -> None:
    """Every hook call is a heartbeat (3.54.0): the record carries `session_id` and `cwd`, so no second hook runs.

    FAILS OPEN and silent on a record with no session: a beat must never change a hook's answer.
    """

    import agents  # noqa: PLC0415

    try:
        from runtime import resolve  # noqa: PLC0415

        agents.beat(resolve()["agent"], record.get("session_id"), "hook", record.get("cwd"))
    except (agents.BeatError, OSError):
        return


def shell_hook(text: str) -> int:
    """`headron shell --hook`: a PreToolUse hook. A refused command is put to the person ("ask"), never denied.

    ADDS, NEVER SUBTRACTS (atlas.yaml/native_agent_tools): the person stays the decider, so the hook
    surfaces the verdict and leaves the tool in place. Exit 0 always; an allowed command prints nothing.
    """
    from agentpolicy import shell_verdict  # noqa: PLC0415

    command = hook_input(text).get("command")
    if not isinstance(command, str) or not command.strip():
        return 0
    verdict = shell_verdict(command)
    _field_refusal(verdict, command)
    if not verdict.allowed:
        _hook_answer(
            "PreToolUse", permissionDecision="deny", permissionDecisionReason=f"headron shell: {verdict.reason}"
        )
    return 0


def edit_guard_hook(text: str) -> int:
    """`headron port --guard`: a PreToolUse hook. A direct edit to the declaration or a generated file is put to the person.

    ASKS, NEVER DENIES, like shell_hook (atlas.yaml/native_agent_tools). Exit 0 always; any other file passes silently.
    """
    import port  # noqa: PLC0415

    path = hook_input(text).get("file_path")
    why = port.declared_only(path) if isinstance(path, str) and path else None
    if why:
        _hook_answer("PreToolUse", permissionDecision="ask", permissionDecisionReason=f"headron edit: {why}")
    return 0


def port_hook(text: str) -> int:
    """`headron port --hook`: a PostToolUse hook. The edited file's one-line plug, and each lesson this session
    has not yet seen, reach the agent as context; only those lessons are sealed as shown (`agents.say_lessons`)."""
    import os  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import port  # noqa: PLC0415

    path = hook_input(text).get("file_path")
    if not isinstance(path, str) or not path:
        return 0
    source = Path(path).expanduser().absolute()
    try:  # the edited file's own repository is the tree, wherever the runtime started this process
        os.chdir(source.resolve().parent)
        rec = port.record(str(source), None, "agent", None)
    except (OSError, ValueError, KeyError):
        return 0
    import atlas as atlas_module  # noqa: PLC0415
    from atlascore import worktree  # noqa: PLC0415

    findings = atlas_module.edited_link_errors(source, worktree())
    if rec["route"] is not None:  # a file no pack routes has no gate to name: silence, not a "none" line
        import agents  # noqa: PLC0415

        said = agents.say_lessons(text, rec["route"], rec.get("lessons"))
        findings = [rec["line"] + port.lock_drift_note(), *said, *findings]
    if findings:
        _hook_answer("PostToolUse", additionalContext="\n".join(findings))
    return 0
