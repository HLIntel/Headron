#!/usr/bin/env python3
"""port — plug any agent into everything Thea knows about what it is touching: one call, three lenses, five frames.

WHY (3.46.0). Thea answers seventy-odd questions, and an agent only ever met the one a hook asked for: the
rest of its value was invisible until someone knew to ask. The port is the socket. Point it at a file, a
directory or a repository and it hands back, in one compact record, what applies there — route, tier, place,
labels, the gates with their exact commands, the ledger's lessons with their moves, the documents to read,
and the NEXT commands worth running — so the next step is taken from Thea rather than guessed.

    thea port [<target>] [--lens narrow|code|codebase] [--frame codebase|chat|tree|model|agent]
              [--runtime <id>] [--json | --line]

LENSES are distances. `narrow` is one file (what must pass before it changes); `code` is one place (what it
is, what it proves, its traps and documents); `codebase` is the whole tree, sorted by TIER — frontend,
middle-frontend, middle, middle-backend, backend, database — so an agent attacking a system sees which layer
a change lands in before it opens a file. The lens is inferred from the target and may be forced.
FRAMES are audiences. `codebase` (default) carries everything; `chat` drops commands for a model with no
shell; `tree` leads with documents and places; `model` adds the model route and the context budgets; `agent`
adds the PLUG — how this runtime loads Thea and which three hooks keep it plugged in.

THE LINE is the braille of the record: fixed glyphs in a fixed order (atlas.yaml/port/glyphs), coloured by
tier when a terminal allows it and plain under NO_COLOR or a pipe, so a person scans it and a model parses it.
EVERY COMMAND HAS A SOCKET: `port_menu_errors` refuses a `thea` command no lens lists in its next steps —
nothing Thea can do stays out of an agent's sight (the rail against its benefits going unused).

WHAT IT DOES NOT PROVE: that a gate passes or a lesson applies — it routes to the things that decide both.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sys
from collections import Counter
from pathlib import Path

from atlascore import ROOT, atlas, ls_files, route_for, strict_yaml, worktree

LENSES = ("narrow", "code", "codebase")
FRAMES = ("codebase", "chat", "tree", "model", "agent")
ANSI = {
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "grey": 90,
    "bright_blue": 94,
    "bright_magenta": 95,
}


def spec() -> dict:
    return dict(atlas().get("port") or {})


def stack_tiers(tree: Path | None = None) -> dict:
    """atlas.yaml/stack_tiers, REPLACED by the tree's own `.atlas.yaml/stack_tiers` when it declares one."""
    own = (tree or worktree()) / ".atlas.yaml"
    if own.is_file() and own.resolve() != (ROOT / ".atlas.yaml").resolve():
        local = (strict_yaml(own.read_text(encoding="utf-8"), ".atlas.yaml") or {}).get("stack_tiers")
        if local:
            return dict(local)
    return dict(atlas().get("stack_tiers") or {})


def tier_of(rel: str, tiers: dict | None = None) -> str:
    """The layer a path belongs to: the first tier whose path pattern matches, then the first whose suffix does."""
    tiers = stack_tiers() if tiers is None else tiers
    for name in tiers:
        if any(re.search(p, rel) for p in (tiers[name] or {}).get("paths") or []):
            return name
    suffix = Path(rel).suffix
    return next((n for n, t in tiers.items() if suffix and suffix in ((t or {}).get("suffixes") or [])), "none")


def _tracked(tree: Path, under: str = "") -> list[str]:
    return ls_files(tree, under or ".")


def lens_for(tree: Path, rel: str) -> str:
    if rel in ("", "."):
        return "codebase"
    return "code" if (tree / rel).is_dir() else "narrow"


def narrow(tree: Path, rel: str) -> dict:
    import atlas as cli  # noqa: PLC0415 — the CLI module owns the gate and plan records
    import dirscope  # noqa: PLC0415
    import knowledge  # noqa: PLC0415

    route = route_for(rel)
    gates = []
    if route:
        plan = cli.plan_record(rel, route, "default", "source_change", [])
        for gate in plan.get("required_gates") or []:
            argv = cli.gate_record(rel, gate).get("argv")
            # INSTALLED IS SAID ON THE ROW (B10): a gate printed without it reads as runnable here, and a
            # missing tool then surfaces as `command not found` blamed on the edit.
            gates.append(
                {
                    "gate": gate,
                    "run": shlex.join(argv) if argv else None,
                    "installed": bool(argv) and bool(shutil.which(argv[0])),
                }
            )
    place_name, place = dirscope.scope_for(rel) if tree == ROOT.resolve() else ("", {})
    labels = [f"lang/{route}"] if route else []
    labels += [str(place.get("label"))] if place.get("label") else []
    return {
        "route": route,
        "place": place_name or None,
        "labels": labels,
        "gates": gates,
        "lessons": knowledge.lessons_for(rel),
    }


def code(tree: Path, rel: str) -> dict:
    import dirscope  # noqa: PLC0415

    files, tiers = _tracked(tree, rel), stack_tiers(tree)
    record = {
        "routes": dict(Counter(r for r in map(route_for, files) if r).most_common(6)),
        "tiers": dict(Counter(tier_of(f, tiers) for f in files).most_common()),
        "read": [f for f in files if f.endswith(".md") and f.count("/") <= rel.count("/") + 2][:12],
    }
    top = rel.split("/", 1)[0]
    if tree == ROOT.resolve() and top in dirscope.scopes():
        row = dirscope.scopes()[top] or {}
        record.update(
            {
                "place": top,
                "is": row.get("is"),
                "proves": row.get("proves") or [],
                "traps": list(row.get("traps") or []),
            }
        )
    return record


def codebase(tree: Path) -> dict:
    files, tiers = _tracked(tree), stack_tiers(tree)
    entries = [e for e in ("README.md", "AGENTS.md", "CLAUDE.md", "llms.txt", ".atlas.yaml") if (tree / e).is_file()]
    return {
        "files": len(files),
        "entries": entries,
        "tiers": dict(Counter(tier_of(f, tiers) for f in files).most_common()),
        "routes": dict(Counter(r for r in map(route_for, files) if r).most_common(8)),
    }


def plug(runtime: str | None) -> dict:
    rows = {str(r.get("id")): r for r in atlas().get("runtime_entry") or []}
    row = rows.get(runtime or "", {})
    return {
        "runtime": runtime,
        "loads": row.get("loads"),
        "adapter": row.get("adapter"),
        "hooks": dict(spec().get("hooks") or {}),
        "runtimes": sorted(rows),
    }


def record(target: str, lens: str | None, frame: str, runtime: str | None, tree: Path | None = None) -> dict:
    """One record for a target. `tree` defaults to the caller's worktree; a target given relative to an
    explicit tree is read there, so a generator draws this atlas from any directory, inside git or not."""
    if tree is None:  # the CLI: a target is relative to where the caller stands
        tree = worktree()
        rel = os.path.relpath(Path(target).resolve(), tree) if target not in ("", ".") else "."
    else:  # a generator: a target is relative to the tree it names, wherever the process stands
        rel = target if target not in ("", ".") else "."
    rel = "." if rel == "." else rel.replace(os.sep, "/")
    lens = lens or lens_for(tree, "" if rel == "." else rel)
    body = narrow(tree, rel) if lens == "narrow" else code(tree, rel) if lens == "code" else codebase(tree)
    out = {
        "schema": "thea-port/1",
        "atlas_version": str(atlas().get("version")),
        "target": rel,
        "lens": lens,
        "frame": frame,
        "tier": tier_of(rel, stack_tiers(tree)) if lens == "narrow" else None,
        **body,
        "next": list((spec().get("menus") or {}).get(lens) or []),
    }
    if frame == "chat":
        out = {k: v for k, v in out.items() if k not in ("gates", "next")}
    elif frame == "model":
        policy = atlas().get("context_policy") or {}
        out["model"] = {
            "routes": atlas().get("model_routes") or {},
            "mcp_server_tokens": policy.get("mcp_server_tokens"),
        }
    elif frame == "agent":
        out["plug"] = plug(runtime)
        if lens == "codebase":  # the lane, not a file: how far the default branch moved under it (3.53.0)
            out["upstream"] = upstream(tree)
    out["line"] = line(out, color=False)
    return out


def upstream(tree: Path) -> dict:
    """The upstream count beside its bound; a None count is NOT RUN (no origin ref), never a clean 0."""
    from upstream import upstream_count  # noqa: PLC0415

    policy = atlas().get("branch_policy") or {}
    base = policy.get("default_base") or "main"
    return {
        "count": upstream_count(tree, base),
        "base": base,
        "bound": (policy.get("upstream_bound") or {}).get("max_behind_commits"),
    }


def _paint(text: str, colour: str | None, on: bool) -> str:
    return f"\033[{ANSI[colour]}m{text}\033[0m" if on and colour in ANSI else text


def line(rec: dict, color: bool) -> str:
    """The braille of the record: fixed glyphs, fixed order, one line — atlas.yaml/port/glyphs names each."""
    g, colours = spec().get("glyphs") or {}, spec().get("colors") or {}
    lens_glyph = (g.get("lens") or {}).get(rec["lens"], "?")
    parts = [f"{lens_glyph} {rec['target']}"]
    if rec.get("tier"):
        tier = rec["tier"]
        parts.append(_paint(f"{(g.get('tier') or {}).get(tier, '·')}{tier}", colours.get(tier), color))
    if rec.get("tiers"):
        parts.append(
            " ".join(
                _paint(f"{(g.get('tier') or {}).get(t, '·')}{n}", colours.get(t), color)
                for t, n in rec["tiers"].items()
                if t != "none"
            )
        )
    parts += [x for x in (rec.get("route"), rec.get("place") and f"{g.get('place', '⌂')}{rec['place']}") if x]
    if rec.get("gates"):
        parts.append(_paint(f"{g.get('gate', '✓')}{len(rec['gates'])}", colours.get("gate"), color))
    if rec.get("lessons"):
        parts.append(_paint(f"{g.get('lesson', '⚠')}{len(rec['lessons'])}", colours.get("lesson"), color))
    if up := rec.get("upstream"):
        over = up["count"] is None or up["bound"] is not None and up["count"] > up["bound"]
        shown = "?" if up["count"] is None else up["count"]
        parts.append(_paint(f"{g.get('upstream', '↓')}{shown}", colours.get("lesson") if over else None, color))
    if rec.get("next"):
        parts.append(f"{g.get('next', '→')} {invocation(rec['next'][0], rec['target'])}")
    return " │ ".join(parts)


def text(rec: dict, color: bool) -> str:
    out = [line(rec, color)]
    for gate in rec.get("gates") or []:
        missing = (
            "  [NOT INSTALLED here: NOT RUN, never a pass]" if gate["run"] and not gate.get("installed", True) else ""
        )
        out.append(f"  gate {gate['gate']}: {gate['run'] or 'no runnable command declared'}{missing}")
    for lesson in rec.get("lessons") or []:
        out.append(f"  lesson {lesson['failure']}" + (f" — do: {lesson['do']}" if lesson.get("do") else ""))
    for trap in rec.get("traps") or []:
        out.append(f"  trap {trap}")
    if rec.get("read"):
        out.append("  read: " + " · ".join(rec["read"][:6]))
    if rec.get("plug"):
        p = rec["plug"]
        out.append(f"  plug {p['runtime'] or '<--runtime>'}: loads {p['loads']} · adapter {p['adapter']}")
        out += [f"  hook {when}: {run}" for when, run in p["hooks"].items()]
    if rec.get("next"):
        out.append("  next: " + " · ".join(invocation(c, rec["target"]) for c in rec["next"][:8]))
    return "\n".join(out)


TARGET_DESTS = ("path", "language")  # positionals the port's own target fills


def invocation(command: str, target: str) -> str:
    """`thea <command>` with every REQUIRED positional filled: the target where the parser names a path,
    `<dest>` elsewhere. Read from the parser, never typed, so a printed next step is one an agent can run
    (B: `thea gate` printed bare exited 2). `port_menu_errors` parses each one back — the renderer is its proof."""
    import commands  # noqa: PLC0415

    row = commands.command_table().get(command) or {}
    words = ["thea", command]
    for action in [a for a in row.get("arguments") or [] if not a.option_strings and a.nargs not in ("?", "*")]:
        words.append(shlex.quote(target) if action.dest in TARGET_DESTS else f"<{action.dest}>")
    return " ".join(words)


PLUG = "atlas.py port"


def loaded_text(rel: str) -> str:
    """What a runtime reads from its entry file, with Claude Code's `@path` imports expanded one level."""
    text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).is_file() else ""
    return "\n".join(
        (ROOT / ln[1:].strip()).read_text(encoding="utf-8")
        if ln.startswith("@") and (ROOT / ln[1:].strip()).is_file()
        else ln
        for ln in text.splitlines()
    )


def plug_line(runtime: str) -> str:
    """The socket as one line, for the file a runtime loads — generated, so no entry file names it by hand."""
    frame = "chat" if runtime == "chat" else "agent"
    hooks = " · ".join(f"{when} `{run}`" for when, run in (spec().get("hooks") or {}).items())
    return f"**Plug in:** `python scripts/{PLUG} <file|dir|.> --frame {frame}`: route, tier, gates, lessons, next steps. Hooks: {hooks}."


def port_menu_errors() -> list[str]:
    """Every `thea` command is reachable from some lens, and every runtime's entry file names the port —
    nothing Thea can do stays out of an agent's sight, and no runtime arrives unplugged."""
    import commands  # noqa: PLC0415

    _, sub = commands.build_parser()
    listed = {c for menu in (spec().get("menus") or {}).values() for c in menu or []}
    errors = [
        f"thea {name} is on no port menu (atlas.yaml/port/menus) — an agent plugged in would never be told it exists"
        for name in sorted(sub.choices)
        if name not in listed and name != "port"
    ]
    errors += [
        f"atlas.yaml/port/menus names `{c}`, which is not a thea command" for c in sorted(listed - set(sub.choices))
    ]
    unknown = [t for t in atlas().get("stack_tiers") or {} if t not in ((spec().get("glyphs") or {}).get("tier") or {})]
    errors += [
        f"{row.get('loads')}: runtime `{row.get('id')}` loads it and it does not name `{PLUG}` — the runtime "
        "is not plugged in"
        for row in atlas().get("runtime_entry") or []
        if PLUG not in loaded_text(str(row.get("loads")))
    ]
    parser = commands.build_parser()[0]
    for name in sorted(listed & set(sub.choices)):
        argv = [w if not w.startswith("<") else "x" for w in invocation(name, "README.md").split()[1:]]
        try:
            with open(os.devnull, "w") as sink, __import__("contextlib").redirect_stderr(sink):
                parser.parse_args(argv)
        except SystemExit:
            errors.append(
                f"port prints `{invocation(name, 'README.md')}`, which `thea` refuses to parse — "
                "a next step an agent cannot run"
            )
    return errors + [f"tier `{t}` has no glyph in atlas.yaml/port/glyphs/tier" for t in unknown]


def main(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="thea port")
    parser.add_argument("target", nargs="?", default=".")
    parser.add_argument("--lens", choices=LENSES)
    parser.add_argument("--frame", choices=FRAMES, default="codebase")
    parser.add_argument("--runtime", default=None, choices=plug(None)["runtimes"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--line", action="store_true")
    args = parser.parse_args(argv)
    rec = record(args.target, args.lens, args.frame, args.runtime)
    color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    print(json.dumps(rec, indent=2) if args.json else line(rec, color) if args.line else text(rec, color))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
