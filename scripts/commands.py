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
  command_table()          each subcommand's parser, help line and arguments — the ONE argparse reader
  argparse_reader_errors() a module outside this one reading argparse privates fails the contract
"""
from __future__ import annotations

import argparse
import json
import re

from atlascore import ROOT, atlas, tracked


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
        if isinstance(done.code, str):  # a refusal's reason: dropped here, it reached the user as a bare 1
            print(done.code, file=sys.stderr)
        return done.code if isinstance(done.code, int) else (0 if done.code is None else 1)
    finally:
        sys.argv = saved
    return 0


def command_table(parser: argparse.ArgumentParser | None = None) -> dict[str, dict]:
    """Each subcommand: its parser, its help line, its arguments (help excluded).

    THE ONE PLACE ARGPARSE INTERNALS ARE READ (3.47.0). argparse has no public way to list a
    subparser's help line or arguments; four modules each reached into the privates, so a stdlib
    change would have broken them one at a time. Every reader calls this instead."""
    parser = parser or build_parser()[0]
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    return {c.dest: {"parser": sub.choices[c.dest], "help": c.help or "",
                     "arguments": [a for a in sub.choices[c.dest]._actions if a.dest != "help"]}  # noqa: SLF001
            for c in sub._choices_actions}  # noqa: SLF001


ARGPARSE_PRIVATE = re.compile(r"\._(?:choices_actions|actions|option_string_actions)\b|_SubParsersAction\b")


def argparse_reader_errors(paths: list | None = None) -> list[str]:
    """Second sighting is a rule: the privates were copied into four modules before command_table."""
    files = paths if paths is not None else [p for p in tracked() if p.suffix == ".py"]
    errors = []
    for path in files:
        path = ROOT / path if not path.is_absolute() else path
        if path.name == "commands.py" or not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if ARGPARSE_PRIVATE.search(line):
                errors.append(f"{path.relative_to(ROOT)}:{number} reads argparse internals — call commands.command_table()")
    return errors


def commands(as_json: bool) -> int:
    """Every command this entry point answers, with the sentence that says what it is for.

    THE ROSTER A HARNESS, AN MCP SERVER OR A FRONT END READS (3.7.0), so none of them keeps its own
    list of what Thea can do. Records are frozen in tools/thea-commands.schema.json.
    """
    table = command_table()
    rows = [{"name": name, "kind": "command", "summary": row["help"],
             "json": any("--json" in a.option_strings for a in row["arguments"])} for name, row in table.items()]
    rows += [{"name": n, "kind": "instrument", "summary": s, "json": False}
             for n, s in sorted(instruments_on_path().items()) if n not in table]
    if as_json:
        print(json.dumps({"schema": "thea-commands/1", "version": atlas().get("version"), "commands": rows}, indent=2))
        return 0
    for row in rows:
        print(f"  {row['name']:<16} {row['kind']:<10} {row['summary'][:96]}")
    print(f"{len(rows)} commands; `thea <command> --help` for one, `thea commands --json` for the record")
    return 0


def cli_errors(parser: argparse.ArgumentParser | None = None) -> list[str]:
    """A command with no help line is a command nobody but its author can find."""
    return [f"command '{name}' has no help line — `thea commands` would list it as a bare name"
            for name, row in command_table(parser).items() if not row["help"].strip()]


OUTPUT_SCHEMA = "tools/atlas-output.schema.json"


def output_schema_errors(parser: argparse.ArgumentParser | None = None, schema: dict | None = None) -> list[str]:
    """Every `--json` command has its record frozen in OUTPUT_SCHEMA, and every record id is declared.

    EARNED BY A REVIEW (3.47.0): the documents said every `--json` record was frozen here, and the schema
    held only a minority of the commands that take `--json`; `port`, the command the entry file tells an
    agent to run first, emitted `thea-port/1` against no declaration. Two halves, because an id can ship two
    ways: a command that takes `--json` needs a `$defs/<command>` entry, offered at the top level, that
    pins its id; and a literal `thea-<name>/<n>` id written in an instrument must be the `const` of some
    schema under tools/, so a record emitted outside the command roster is declared somewhere too.
    """
    import re  # noqa: PLC0415
    parser = parser or build_parser()[0]
    tools = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "tools").glob("*.schema.json"))}
    schema = schema if schema is not None else tools.get(OUTPUT_SCHEMA.rsplit("/", 1)[1], {})
    defs, offered = schema.get("$defs") or {}, {str(r.get("$ref")) for r in schema.get("oneOf") or []}
    roster_ids = {str(((s.get("properties") or {}).get("schema") or {}).get("const")) for s in tools.values()}
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    errors = []
    for name, cmd in sub.choices.items():
        if not any("--json" in a.option_strings for a in cmd._actions) or f"thea-{name}/1" in roster_ids:  # noqa: SLF001
            continue
        props = (defs.get(name) or {}).get("properties") or {}
        pinned = (props.get("command") or {}).get("const") == name or \
            re.fullmatch(rf"thea-{re.escape(name)}/\d+", str((props.get("schema") or {}).get("const")))
        if f"#/$defs/{name}" not in offered or not pinned:
            errors.append(f"`thea {name} --json` emits a record {OUTPUT_SCHEMA} does not freeze — add $defs/{name} "
                          "pinning its id and offer it in the top-level oneOf")
    declared = {str(c) for s in tools.values() for c in re.findall(r'"const":\s*"(thea-[a-z-]+/\d+)"', json.dumps(s))}
    for path in sorted((ROOT / "scripts").glob("*.py")):
        if path.name.endswith("_test.py"):
            continue
        for rid in sorted(set(re.findall(r"[\"'](thea-[a-z-]+/\d+)[\"']", path.read_text(encoding="utf-8"))) - declared):
            errors.append(f"scripts/{path.name} emits record id {rid} that no tools/*.schema.json declares")
    return errors


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
    verify_parser.add_argument("--fresh", action="store_true", help="with --changed, ignore byte-identical local evidence and re-measure")
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
    search_parser = sub.add_parser("index-search", help="search the chunk index; every hit carries its citation")
    search_parser.add_argument("query", nargs="+")
    search_parser.add_argument("--limit", type=int, default=5)
    do_parser = sub.add_parser("do", help="a pack action for a file (build, test, run); printed unless --run")
    do_parser.add_argument("path")
    do_parser.add_argument("action", nargs="?", default=None, help="a key of atlas.yaml/pack_actions")
    do_parser.add_argument("--run", action="store_true", help="execute it; printing is the default")
    pick_parser = sub.add_parser("pick", help="choose a language along a declared axis")
    pick_parser.add_argument("axis", nargs="?", default=None, help="a key of atlas.yaml/language_selection")
    decide_parser = sub.add_parser("decide", help="a system-design decision: options, when, failure, proof")
    decide_parser.add_argument("id", nargs="?", default=None, help="a key of systems/decisions.yaml")
    decide_parser.add_argument("--json", action="store_true", help="emit the record as JSON")
    judge_parser = sub.add_parser("judge", help="a closed question answered with p: act above the declared bar, else ask")
    judge_parser.add_argument("id", nargs="?", default=None, help="a key of systems/judgments.yaml")
    judge_parser.add_argument("answer", nargs="?", default=None)
    judge_parser.add_argument("p", nargs="?", default=None, help="the probability of that answer, 0..1")
    judge_parser.add_argument("--fact", action="append", default=[], help="a declared fact; it forces its answer")
    judge_parser.add_argument("--calibrate", default=None, metavar="TSV", help="score every bar against id/answer/p/pass|fail rows")
    intake_parser = sub.add_parser("intake", help="digest a user's prompt into a task, or the questions that make it one")
    intake_parser.add_argument("prompt", nargs="+", help="the prompt, as the user wrote it")
    intake_parser.add_argument("--json", action="store_true", help="emit the task as JSON")
    shell_parser = sub.add_parser("shell", help="refuse a shell string whose verdict or effect is not the one its writer reads")
    # NOT `command`: argparse would overwrite the subcommand name the dispatcher reads (3.27.0).
    shell_parser.add_argument("cmd", nargs="+", help="the shell string, exactly as it would run")
    shell_parser.add_argument("--json", action="store_true", help="emit the verdict as a record")
    delegate_parser = sub.add_parser("delegate", help="what a handoff to another agent must carry, and why")
    delegate_parser.add_argument("--task", default=None, help="what the delegate is for")
    delegate_parser.add_argument("--json", action="store_true", help="emit the brief as JSON")
    handoff_parser = sub.add_parser("handoff", help="a bounded handoff for one artifact: route, context and acceptance")
    handoff_parser.add_argument("path", help="the artifact the recipient may work on")
    handoff_parser.add_argument("--task", default=None, help="the outcome this artifact serves")
    handoff_parser.add_argument("--change", default="source_change", help="a declared verification change class")
    handoff_parser.add_argument("--json", action="store_true", help="emit the capsule as JSON")
    cadence_parser = sub.add_parser("cadence", help="the time-boxed session as a clock: phases, reserve, expiry rule")
    cadence_parser.add_argument("--minutes", type=float, default=None, help="scale the declared box to this many minutes")
    cadence_parser.add_argument("--json", action="store_true", help="emit the schedule as JSON")
    sched_parser = sub.add_parser("schedtargets", help="every active scheduled job's target exists on this host")
    sched_parser.add_argument("--root", default=None, help="a fixture home to sweep instead of the real one")
    sched_parser.add_argument("--platform", default=None, help="darwin or linux; defaults to this host")
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
    failures_parser.add_argument("--for", dest="for_", default=None,
                                 help="a file or task: only the shapes most relevant to it, with their tells")
    failures_parser.add_argument("--limit", type=int, default=3, help="how many shapes --for returns")
    successes_parser = sub.add_parser("successes", help="the moves that replaced recorded failures: what to do, when, and how to prove it")
    successes_parser.add_argument("id", nargs="?", default=None, help="a key of atlas.yaml/agent_success_patterns")
    successes_parser.add_argument("--json", action="store_true", help="emit the moves as JSON")
    successes_parser.add_argument("--for", dest="for_", default=None, help="a file or task: only the moves most relevant to it")
    successes_parser.add_argument("--limit", type=int, default=3, help="how many moves --for returns")
    md_parser = sub.add_parser("md", help="Markdown by class: living capped and reachable, records append-only, generated left alone")
    md_parser.add_argument("repo", nargs="?", default=None, help="a repository; the caller's own when omitted")
    md_parser.add_argument("--staged", action="store_true", help="the commit gate: a staged record may only grow")
    md_parser.add_argument("--base", default=None, help="a ref: may this branch have rewritten a record?")
    landed_parser = sub.add_parser("landed", help="does the base hold every change on a branch? Ask before closing or deleting it")
    landed_parser.add_argument("branch", help="a branch or ref, e.g. origin/feature")
    landed_parser.add_argument("--base", default="origin/main", help="the ref the work should have reached")
    brainstorm_parser = sub.add_parser("brainstorm", help="a strategic brainstorm as a checked record: diverge, pre-mortem, converge, prove")
    brainstorm_parser.add_argument("record", nargs="*", help="a brainstorm record (.yaml); with --new, the question")
    brainstorm_parser.add_argument("--new", action="store_true", help="print a skeleton record for the question")
    brainstorm_parser.add_argument("--json", action="store_true", help="emit the findings as a record")
    port_parser = sub.add_parser("port", help="PLUG IN: route, tier, gates, lessons and next commands for a file, place or tree")
    port_parser.add_argument("target", nargs="?", default=".", help="a file, a directory, or . for the tree")
    port_parser.add_argument("--lens", choices=["narrow", "code", "codebase"], help="force the distance; inferred otherwise")
    port_parser.add_argument("--frame", choices=["codebase", "chat", "tree", "model", "agent"], default="codebase",
                             help="the audience: chat drops commands, model adds routes, agent adds the plug")
    port_parser.add_argument("--runtime", default=None, help="a runtime_entry id, for --frame agent")
    port_parser.add_argument("--json", action="store_true", help="emit the record as JSON")
    port_parser.add_argument("--line", action="store_true", help="one glyph line, nothing else")
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
    compile_parser = sub.add_parser("compile", help="a .thea program as the task contract every control reads")
    compile_parser.add_argument("path", help="a .thea program")
    compile_parser.add_argument("--explain", action="store_true",
                                help="add where each element is decided, the labels it carries and "
                                     "the place it works in")
    compile_parser.add_argument("--labels", action="store_true",
                                help="print only the labels this program files under, one per line")
    plan_parser = sub.add_parser("plan", help="the gates a task and change class need for a path")
    plan_parser.add_argument("path")
    plan_parser.add_argument("--task", default="default", help="a key of atlas.yaml/task_profiles")
    plan_parser.add_argument("--change", default=None, help="a key of atlas.yaml/verification_policy/profiles")
    plan_parser.add_argument("--modifier", action="append", default=[], dest="modifiers",
                             help="a key of atlas.yaml/risk_modifiers; repeatable, and it only ADDS gates")
    plan_parser.add_argument("--json", action="store_true", help="emit the plan as a JSON record")
    plan_parser.add_argument("--thea", action="store_true",
                             help="emit a starter .thea program for this plan — route, profile, change "
                                  "class and gates as resolved, with the allowances derived from the "
                                  "gate commands and the effects from those allowances")
    plan_parser.add_argument("--objective", default=None,
                             help="one sentence: what would make this task DONE. Required by --thea, "
                                  "because it is the one field nothing in the tree can derive")
    return parser, sub
