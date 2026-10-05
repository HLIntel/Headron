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
        if (script.startswith("scripts/") and script.endswith(".py") and not script.endswith("_test.py")
                and (ROOT / script).is_file() and runs_when_executed((ROOT / script).read_text(encoding="utf-8"))):
            rows[script.removeprefix("scripts/").removesuffix(".py")] = " ".join(str(row.get("proves") or "").split())
    return rows


def runs_when_executed(source: str) -> bool:
    """A LIBRARY IS NOT AN INSTRUMENT: `thea atlascore` ran a module that only defines, printed nothing and
    exited 0 — a blind run reading as a pass. Runnable: a `__main__` block, or a top-level loop or bare call
    (`main()`, `print()`); `TABLE.update(...)` is setup, not a run."""
    import ast

    from atlascore import parsed_python
    tree = parsed_python(source, "instrument")
    return tree is not None and any(
        isinstance(node, ast.If) and "__main__" in ast.unparse(node.test) or isinstance(node, (ast.For, ast.While, ast.With))
        or isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
        for node in tree.body)


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
             "json": any("--json" in a.option_strings for a in row["arguments"]),
             "arguments": [a.option_strings[-1] if a.option_strings else a.dest for a in row["arguments"]]}
            for name, row in table.items()]
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
    """A command with no help line, or an instrument `thea --help` never names, is one nobody but its
    author can find; a command with no --json and no stated reason is one a program cannot read."""
    parser = parser or build_parser()[0]
    table = command_table(parser)
    return [f"command '{name}' has no help line — `thea commands` would list it as a bare name"
            for name, row in table.items() if not row["help"].strip()] + [
        f"instrument '{name}' runs as `thea {name}` and `thea --help` does not name it (#19)"
        for name in sorted(set(instruments_on_path()) - set(table)
                           - set(re.findall(r"[\w-]+", (parser.epilog or "").partition("):")[2])))] + [
        f"command '{name}' takes no --json and COMMAND_ROWS says nothing of why (#16)"
        for name, row in table.items()
        if not any("--json" in a.option_strings for a in row["arguments"]) and not NO_JSON.get(name)]


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


def _arg(*flags: str, **kw) -> tuple[tuple[str, ...], dict]:
    return flags, kw


_ON = {"action": "store_true"}
# EVERY COMMAND, ONE ROW (#26): name, help line, the --json cell, the other arguments. The --json cell
# means one of two things (#16): text that starts "emit" is the flag's help; any other text says WHY the
# command takes no --json. `cli_errors` refuses a command whose parser carries neither.
COMMAND_ROWS: tuple[tuple[str, str, str, tuple], ...] = (
    ("commands", "every command and instrument, as text or a JSON record", "emit the roster as a JSON record", ()),
    ("check", "the whole contract; the exit code is the verdict", "emit every finding with its severity as a record", (
        _arg("--fix", **_ON, help="repair what is MECHANICAL — regenerate drifted blocks, tighten a ratchet to what "
             "the tree costs — then re-check. It never raises a bound and never repairs a decision"),)),
    ("verify", "every done gate once: PASS, FAIL or NOT RUN, by exit code", "emit the verdicts as a record", (
        _arg("--changed", **_ON, help="only the changed files' own gates, plus the contract"),
        _arg("--fresh", **_ON, help="with --changed, ignore byte-identical local evidence and re-measure"))),
    ("invariants", "every hard invariant and the function that enforces it",
     "a violated invariant fails `thea check`, whose --json carries it as a finding", ()),
    ("doctor", "can the contract run here: interpreter, parser, toolchains", "emit the environment as a record", ()),
    ("index", "regenerate the generated documents (--write) or show the drift",
     "it writes or diffs generated files; the exit code is the verdict", (_arg("--write", **_ON),)),
    ("learn", "the guide, card and tools one language needs, and nothing else",
     "it prints documents for a model to read; `thea route --json` is the record",
     (_arg("language", help="a route (python, quantum/qsharp) or a file to route"),)),
    ("process", "a named process: gates, artifacts, when to stop or escalate", "emit the process as a JSON record",
     (_arg("id", nargs="?", default=None, help="a key of atlas.yaml/processes"),)),
    ("index-search", "search the chunk index; every hit carries its citation",
     "each hit is already a citation line: path, lines, blob and contract version",
     (_arg("query", nargs="+"), _arg("--limit", type=int, default=5))),
    ("do", "a pack action for a file (build, test, run); printed unless --run",
     "it prints one command, or runs it and the output is the tool's own", (
        _arg("path"), _arg("action", nargs="?", default=None, help="a key of atlas.yaml/pack_actions"),
        _arg("--run", **_ON, help="execute it; printing is the default"))),
    ("pick", "choose a language along a declared axis",
     "it prints atlas.yaml/language_selection, which is already the structured form",
     (_arg("axis", nargs="?", default=None, help="a key of atlas.yaml/language_selection"),)),
    ("decide", "a system-design decision: options, when, failure, proof", "emit the record as JSON",
     (_arg("id", nargs="?", default=None, help="a key of systems/decisions.yaml"),)),
    ("judge", "a closed question answered with p: act above the declared bar, else ask",
     "it reads systems/judgments.yaml, which is already the structured form", (
        _arg("id", nargs="?", default=None, help="a key of systems/judgments.yaml"),
        _arg("answer", nargs="?", default=None),
        _arg("p", nargs="?", default=None, help="the probability of that answer, 0..1"),
        _arg("--fact", action="append", default=[], help="a declared fact; it forces its answer"),
        _arg("--calibrate", default=None, metavar="TSV", help="score every bar against id/answer/p/pass|fail rows"))),
    ("intake", "digest a user's prompt into a task, or the questions that make it one", "emit the task as JSON",
     (_arg("prompt", nargs="+", help="the prompt, as the user wrote it"),)),
    # `cmd`, NOT `command`: argparse would overwrite the subcommand name the dispatcher reads (3.27.0).
    ("shell", "refuse a shell string whose verdict or effect is not the one its writer reads",
     "emit the verdict as a record", (
        _arg("cmd", nargs="*", help="the shell string, exactly as it would run"),
        _arg("--hook", **_ON, help="read a PreToolUse record on stdin; a refusal asks, never denies"))),
    ("delegate", "what a handoff to another agent must carry, and why", "emit the brief as JSON",
     (_arg("--task", default=None, help="what the delegate is for"),)),
    ("handoff", "a bounded handoff for one artifact: route, context and acceptance", "emit the capsule as JSON", (
        _arg("path", help="the artifact the recipient may work on"),
        _arg("--task", default=None, help="the outcome this artifact serves"),
        _arg("--change", default="source_change", help="a declared verification change class"))),
    ("cadence", "the time-boxed session as a clock: phases, reserve, expiry rule", "emit the schedule as JSON",
     (_arg("--minutes", type=float, default=None, help="scale the declared box to this many minutes"),)),
    ("schedtargets", "every active scheduled job's target exists on this host",
     "one FAIL or WARN line per job; the exit code is the verdict", (
        _arg("--root", default=None, help="a fixture home to sweep instead of the real one"),
        _arg("--platform", default=None, help="darwin or linux; defaults to this host"))),
    ("role", "what an agent in a role may do, hands back, and when it ends", "emit the role as JSON",
     (_arg("name", nargs="?", default=None, help="a key of atlas.yaml/agent_roles"),)),
    ("resume", "where interrupted work stands, and the one next action", "emit the state as JSON", ()),
    ("steps", "the ordered implementation plan for one runtime, to its return point", "emit the steps as JSON", (
        _arg("path"),
        _arg("--runtime", default="claude", help="a runtime_entry id: claude, openai_codex, cursor, chat, ..."),
        _arg("--change", default="source_change", help="a key of verification_policy/profiles"),
        _arg("--tier", default="mid", choices=["small", "mid", "frontier"],
             help="scaffolding for the model's size: small adds a work loop and a scope fence"))),
    ("failures", "the ledger of mistakes agents made here, each with its guard", "emit the ledger as JSON", (
        _arg("id", nargs="?", default=None, help="a key of atlas.yaml/agent_failure_modes"),
        _arg("--for", dest="for_", default=None, help="a file or task: only the shapes most relevant to it, with their tells"),
        _arg("--limit", type=int, default=3, help="how many shapes --for returns"))),
    ("successes", "the moves that replaced recorded failures: what to do, when, and how to prove it",
     "emit the moves as JSON", (
        _arg("id", nargs="?", default=None, help="a key of atlas.yaml/agent_success_patterns"),
        _arg("--for", dest="for_", default=None, help="a file or task: only the moves most relevant to it"),
        _arg("--limit", type=int, default=3, help="how many moves --for returns"))),
    ("md", "Markdown by class: living capped and reachable, records append-only, generated left alone",
     "one finding per line; the exit code is the verdict", (
        _arg("repo", nargs="?", default=None, help="a repository; the caller's own when omitted"),
        _arg("--staged", **_ON, help="the commit gate: a staged record may only grow"),
        _arg("--base", default=None, help="a ref: may this branch have rewritten a record?"))),
    ("landed", "does the base hold every change on a branch? Ask before closing or deleting it",
     "the exit code is the answer; the rest lists what the base lacks", (
        _arg("branch", help="a branch or ref, e.g. origin/feature"),
        _arg("--base", default="origin/main", help="the ref the work should have reached"))),
    ("brainstorm", "a strategic brainstorm as a checked record: diverge, pre-mortem, converge, prove",
     "emit the findings as a record", (
        _arg("record", nargs="*", help="a brainstorm record (.yaml); with --new, the question"),
        _arg("--new", **_ON, help="print a skeleton record for the question"))),
    ("port", "PLUG IN: route, tier, gates, lessons and next commands for a file, place or tree",
     "emit the record as JSON", (
        _arg("target", nargs="?", default=".", help="a file, a directory, or . for the tree"),
        _arg("--lens", choices=["narrow", "code", "codebase"], help="force the distance; inferred otherwise"),
        _arg("--frame", choices=["codebase", "chat", "tree", "model", "agent"], default="codebase",
             help="the audience: chat drops commands, model adds routes, agent adds the plug"),
        _arg("--runtime", default=None, help="a runtime_entry id, for --frame agent"),
        _arg("--line", **_ON, help="one glyph line, nothing else"),
        _arg("--hook", **_ON, help="read a PostToolUse record on stdin; answer the edited file's plug"))),
    ("why", "why a rule is asymmetric, from atlas.yaml/asymmetries",
     "it prints atlas.yaml/asymmetries, which is already the structured form",
     (_arg("id", nargs="?", default=None, help="a key of atlas.yaml/asymmetries"),)),
    ("gate", "the one command a gate runs for a file — the cheapest answer", "emit the resolution as a JSON record", (
        _arg("path"),
        _arg("gate", nargs="?", help="a key of atlas.yaml/gate_tools; omit it for every gate the change needs"),
        _arg("--change", default="source_change", help="the change class, when no gate is named"))),
    ("route", "pack, card, manifest, lane and the rule that resolved a path", "emit the route as a JSON record",
     (_arg("path"),)),
    ("compile", "a .thea program as the task contract every control reads", "it always prints its record as JSON", (
        _arg("path", help="a .thea program"),
        _arg("--explain", **_ON, help="add where each element is decided, the labels it carries and the place it "
             "works in"),
        _arg("--labels", **_ON, help="print only the labels this program files under, one per line"))),
    ("plan", "the gates a task and change class need for a path", "emit the plan as a JSON record", (
        _arg("path"),
        _arg("--task", default="default", help="a key of atlas.yaml/task_profiles"),
        _arg("--change", default=None, help="a key of atlas.yaml/verification_policy/profiles"),
        _arg("--modifier", action="append", default=[], dest="modifiers",
             help="a key of atlas.yaml/risk_modifiers; repeatable, and it only ADDS gates"),
        _arg("--thea", **_ON, help="emit a starter .thea program for this plan — route, profile, change class and "
             "gates as resolved, with the allowances derived from the gate commands and the effects from those "
             "allowances"),
        _arg("--objective", default=None, help="one sentence: what would make this task DONE. Required by --thea, "
             "because it is the one field nothing in the tree can derive"))),
)
NO_JSON = {name: why for name, _, why, _ in COMMAND_ROWS if not why.startswith("emit")}


def build_parser() -> tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    parser = argparse.ArgumentParser(prog="thea", description="Thea Software: route, gate, plan and verify "
                                     "any file for any AI. `thea commands` lists everything, instruments included.",
                                     epilog="instruments, run by name (`thea commands` says what each proves): "
                                     + ", ".join(sorted(instruments_on_path())))
    parser.add_argument("--version", action="version", version=f"thea {atlas().get('version')}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_line, json_cell, args in COMMAND_ROWS:
        command = sub.add_parser(name, help=help_line)
        for flags, kw in args + ((_arg("--json", **_ON, help=json_cell),) if name not in NO_JSON else ()):
            command.add_argument(*flags, **kw)
    return parser, sub
