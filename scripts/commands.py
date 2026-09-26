#!/usr/bin/env python3
"""What Thea answers, in one place: the parser, the roster, and dispatch to declared instruments.

WHY ITS OWN MODULE (3.7.0). The CLI, the MCP server and any future front end must agree on what
Thea can do. Kept inside atlas.py, the roster was reachable only by parsing help text; here each
reader imports the same parser and the same instrument list, so none of them keeps a copy.

  build_parser()           the argparse tree `thea` answers
  commands(as_json)        every command and instrument, with the sentence that says what it is for
  instruments_on_path()    declared instruments runnable by name, derived from atlas.yaml/instruments
  run_instrument(n, argv)  run one in this process with its own argv; its exit code is returned
  cli_errors()             a command with no help line fails the contract
"""
from __future__ import annotations

import argparse
import json

from atlascore import ROOT, atlas


def instruments_on_path() -> dict[str, str]:
    """Declared instruments a user can run by name through this entry point: stem -> what it proves.

    DERIVED FROM atlas.yaml/instruments, never a second list (3.7.0): before this, `enforce`,
    `staleness` and `branchstate` were reachable only as `python scripts/<name>.py` from a checkout,
    so an agent handed `thea` could route and gate but not enforce, land or review drift.
    """
    rows = {}
    for row in (atlas().get("instruments") or {}).values():
        script = str((row or {}).get("script") or "")
        if script.startswith("scripts/") and script.endswith(".py") and not script.endswith("_test.py"):
            rows[script.removeprefix("scripts/").removesuffix(".py")] = " ".join(str(row.get("proves") or "").split())
    return rows


def run_instrument(name: str, argv: list[str]) -> int:
    """Run a declared instrument's own main, in this process, with its own argv."""
    import runpy
    import sys
    saved = sys.argv
    sys.argv = [f"scripts/{name}.py", *argv]
    try:
        runpy.run_path(str(ROOT / "scripts" / f"{name}.py"), run_name="__main__")
    except SystemExit as done:
        return done.code if isinstance(done.code, int) else (0 if done.code is None else 1)
    finally:
        sys.argv = saved
    return 0


def commands(as_json: bool) -> int:
    """Every command this entry point answers, with the sentence that says what it is for.

    THE ROSTER A HARNESS, AN MCP SERVER OR A FRONT END READS (3.7.0), so none of them keeps its own
    list of what Thea can do. Records are frozen in tools/thea-commands.schema.json.
    """
    parser, _ = build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    rows = [{"name": c.dest, "kind": "command", "summary": c.help or "",
             "json": any("--json" in a.option_strings for a in sub.choices[c.dest]._actions)}  # noqa: SLF001
            for c in sub._choices_actions]  # noqa: SLF001
    rows += [{"name": n, "kind": "instrument", "summary": s, "json": False}
             for n, s in sorted(instruments_on_path().items()) if n not in sub.choices]
    if as_json:
        print(json.dumps({"schema": "thea-commands/1", "version": atlas().get("version"), "commands": rows}, indent=2))
        return 0
    for row in rows:
        print(f"  {row['name']:<16} {row['kind']:<10} {row['summary'][:96]}")
    print(f"{len(rows)} commands; `thea <command> --help` for one, `thea commands --json` for the record")
    return 0


def cli_errors(parser: argparse.ArgumentParser | None = None) -> list[str]:
    """A command with no help line is a command nobody but its author can find."""
    parser = parser or build_parser()[0]
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    return [f"command '{c.dest}' has no help line — `thea commands` would list it as a bare name"
            for c in sub._choices_actions if not (c.help or "").strip()]  # noqa: SLF001


def build_parser() -> tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    parser = argparse.ArgumentParser(prog="thea", description="Thea Software: route, gate, plan and verify "
                                     "any file for any AI. `thea commands` lists everything, instruments included.")
    sub = parser.add_subparsers(dest="command", required=True)
    commands_parser = sub.add_parser("commands", help="every command and instrument, as text or a JSON record")
    commands_parser.add_argument("--json", action="store_true", help="emit the roster as a JSON record")
    check_parser = sub.add_parser("check", help="the whole contract; the exit code is the verdict")
    check_parser.add_argument("--json", action="store_true", help="emit every finding with its severity as a record")
    verify_parser = sub.add_parser("verify", help="every done gate once: PASS, FAIL or NOT RUN, by exit code")
    verify_parser.add_argument("--json", action="store_true", help="emit the verdicts as a record")
    verify_parser.add_argument("--changed", action="store_true", help="only the changed files' own gates, plus the contract")
    check_parser.add_argument("--fix", action="store_true",
                              help="repair what is MECHANICAL — regenerate drifted blocks, tighten a "
                                   "ratchet to what the tree costs — then re-check. It never raises a "
                                   "bound and never repairs a decision")
    sub.add_parser("invariants", help="every hard invariant and the function that enforces it")
    doctor_parser = sub.add_parser("doctor", help="can the contract run here: interpreter, parser, toolchains")
    doctor_parser.add_argument("--json", action="store_true", help="emit the environment as a record")
    index_parser = sub.add_parser("index", help="regenerate the generated documents (--write) or show the drift")
    index_parser.add_argument("--write", action="store_true")
    learn_parser = sub.add_parser("learn", help="the guide, card and tools one language needs, and nothing else")
    learn_parser.add_argument("language", help="a route (python, quantum/qsharp) or a file to route")
    process_parser = sub.add_parser("process", help="a named process: gates, artifacts, when to stop or escalate")
    process_parser.add_argument("id", nargs="?", default=None, help="a key of atlas.yaml/processes")
    process_parser.add_argument("--json", action="store_true", help="emit the process as a JSON record")
    index_parser = sub.add_parser("index-search", help="search the chunk index; every hit carries its citation")
    index_parser.add_argument("query", nargs="+")
    index_parser.add_argument("--limit", type=int, default=5)
    do_parser = sub.add_parser("do", help="a pack action for a file (build, test, run); printed unless --run")
    do_parser.add_argument("path")
    do_parser.add_argument("action", nargs="?", default=None, help="a key of atlas.yaml/pack_actions")
    do_parser.add_argument("--run", action="store_true", help="execute it; printing is the default")
    pick_parser = sub.add_parser("pick", help="choose a language along a declared axis")
    pick_parser.add_argument("axis", nargs="?", default=None, help="a key of atlas.yaml/language_selection")
    decide_parser = sub.add_parser("decide", help="a system-design decision: options, when, failure, proof")
    decide_parser.add_argument("id", nargs="?", default=None, help="a key of systems/decisions.yaml")
    decide_parser.add_argument("--json", action="store_true", help="emit the record as JSON")
    intake_parser = sub.add_parser("intake", help="digest a user's prompt into a task, or the questions that make it one")
    intake_parser.add_argument("prompt", nargs="+", help="the prompt, as the user wrote it")
    intake_parser.add_argument("--json", action="store_true", help="emit the task as JSON")
    cadence_parser = sub.add_parser("cadence", help="the time-boxed session as a clock: phases, reserve, expiry rule")
    cadence_parser.add_argument("--minutes", type=float, default=None, help="scale the declared box to this many minutes")
    cadence_parser.add_argument("--json", action="store_true", help="emit the schedule as JSON")
    role_parser = sub.add_parser("role", help="what an agent in a role may do, hands back, and when it ends")
    role_parser.add_argument("name", nargs="?", default=None, help="a key of atlas.yaml/agent_roles")
    role_parser.add_argument("--json", action="store_true", help="emit the role as JSON")
    resume_parser = sub.add_parser("resume", help="where interrupted work stands, and the one next action")
    resume_parser.add_argument("--json", action="store_true", help="emit the state as JSON")
    steps_parser = sub.add_parser("steps", help="the ordered implementation plan for one runtime, to its return point")
    steps_parser.add_argument("path")
    steps_parser.add_argument("--runtime", default="claude", help="a runtime_entry id: claude, openai_codex, cursor, chat, ...")
    steps_parser.add_argument("--change", default="source_change", help="a key of verification_policy/profiles")
    steps_parser.add_argument("--json", action="store_true", help="emit the steps as JSON")
    steps_parser.add_argument("--tier", default="mid", choices=["small", "mid", "frontier"],
                              help="scaffolding for the model's size: small adds a work loop and a scope fence")
    failures_parser = sub.add_parser("failures", help="the ledger of mistakes agents made here, each with its guard")
    failures_parser.add_argument("id", nargs="?", default=None, help="a key of atlas.yaml/agent_failure_modes")
    failures_parser.add_argument("--json", action="store_true", help="emit the ledger as JSON")
    why_parser = sub.add_parser("why", help="why a rule is asymmetric, from atlas.yaml/asymmetries")
    why_parser.add_argument("id", nargs="?", default=None, help="a key of atlas.yaml/asymmetries")
    gate_parser = sub.add_parser("gate", help="the one command a gate runs for a file — the cheapest answer")
    gate_parser.add_argument("path")
    gate_parser.add_argument("gate", nargs="?", help="a key of atlas.yaml/gate_tools; omit it for every gate the change needs")
    gate_parser.add_argument("--change", default="source_change", help="the change class, when no gate is named")
    gate_parser.add_argument("--json", action="store_true", help="emit the resolution as a JSON record")
    route_parser = sub.add_parser("route", help="pack, card, manifest, lane and the rule that resolved a path")
    route_parser.add_argument("path")
    route_parser.add_argument("--json", action="store_true", help="emit the route as a JSON record")
    plan_parser = sub.add_parser("plan", help="the gates a task and change class need for a path")
    plan_parser.add_argument("path")
    plan_parser.add_argument("--task", default="default", help="a key of atlas.yaml/task_profiles")
    plan_parser.add_argument("--change", default=None, help="a key of atlas.yaml/verification_policy/profiles")
    plan_parser.add_argument("--modifier", action="append", default=[], dest="modifiers",
                             help="a key of atlas.yaml/risk_modifiers; repeatable, and it only ADDS gates")
    plan_parser.add_argument("--json", action="store_true", help="emit the plan as a JSON record")
    return parser, sub
