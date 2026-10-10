"""`thea links`: where this release is, and what each companion reads from it. Read-only.

TheaOS and the Thea site both depend on this repository and used to carry their own copy of
what they depend on: a release tag typed into a download link, a command list typed into a panel table.
Both drifted (a site pinned to the previous tag; a TheaOS page waiting for a command that had shipped).
This record is the one place that states it, from `atlas.yaml/companions` and the declared identity.

Every command a companion consumes is checked against the parser that serves it: a row naming a command
that is gone reports `present: false` and the exit is 1. The record names no companion's repository: the
public tree carries only what a reader outside the owner can use.

FLAGS ARE PART OF THE CONTRACT (3.55.0). TheaOS reads `port --hook` and `failures --match`, not `port` and
`failures`: a flag renamed under a present verb broke the host as surely as a removed verb, and only the
verb was checked. Each `--flag` in a consumed argv must be an option of that verb's own parser. A companion
that `drives` a process consumes every argv that process's `host_calls` names, so the hook wiring a host
derives from `thea process <id> --json` cannot ask for a call the companion row never declared.
`thea check` runs `companion_errors` under every_command_has_a_socket, so a consumed call that is gone fails
the contract, not only this page.
"""

from __future__ import annotations

import json
import sys

from atlascore import atlas

RAW = "https://raw.githubusercontent.com"
DOCUMENTS = ("README.md", "CHAT.md", "SECURITY.md", "LICENSE", "llms.txt")


def release() -> dict:
    """The addresses a page or an app links to, all built from the declared owner, repository and version."""
    contract = atlas()
    identity = contract["identity"]
    repo = f"https://github.com/{identity['owner']}/{identity['repository']}"
    tag = f"v{contract['version']}"
    return {
        "version": contract["version"],
        "tag": tag,
        "repository": repo,
        "archive": f"{repo}/archive/refs/tags/{tag}.zip",
        "documents": {
            name: {
                "at_tag": f"{repo}/blob/{tag}/{name}",
                "latest": f"{repo}/blob/main/{name}",
                "raw_latest": f"{RAW}/{identity['owner']}/{identity['repository']}/main/{name}",
            }
            for name in DOCUMENTS
        },
        "install": {
            key: {"label": row["label"], "command": row["command"].format(repo=repo, tag=tag)}
            for key, row in contract["install_commands"].items()
        },
    }


def served_options() -> dict[str, set[str]]:
    """Each verb and the option strings its own parser accepts."""
    from commands import command_table  # noqa: PLC0415

    return {
        name: {flag for action in row["arguments"] for flag in action.option_strings}
        for name, row in command_table().items()
    }


def served(argv: str, options: dict[str, set[str]] | None = None) -> bool:
    """Does the parser serve this argv: its verb, and every `--flag` it names under that verb?"""
    options = options if options is not None else served_options()
    verb, *rest = str(argv).split() or [""]
    return verb in options and all(w in options[verb] for w in rest if w.startswith("-"))


def host_calls(process: str) -> list[str]:
    """The argv a host runs for a process, from `atlas.yaml/processes/<id>/host_calls`."""
    spec = (atlas().get("processes") or {}).get(process) or {}
    return [str(call.get("argv")) for call in spec.get("host_calls") or []]


def companions() -> list[dict]:
    """One row per declared companion, each consumed command read back against the parser."""
    options = served_options()
    rows = []
    for name, row in (atlas().get("companions") or {}).items():
        consumes = [{"argv": argv, "present": served(argv, options)} for argv in row.get("consumes") or []]
        rows.append(
            {
                "id": name,
                "what": row["what"],
                "where": row["where"],
                "available_to": row["available_to"],
                "consumes": consumes,
            }
        )
    return rows


def host_call_errors(name: str, spec: dict) -> list[str]:
    """A host call serves a step of its own process, runs an argv the parser serves, and has a deadline.

    A call naming a step the process does not run, a flag the verb lost, or no deadline is a hook that
    fires on nothing, fails, or hangs the turn it serves."""
    errors = []
    for call in spec.get("host_calls") or []:
        call = call or {}
        if str(call.get("step")) not in [str(s) for s in spec.get("sequence") or []]:
            errors.append(
                f"processes/{name}/host_calls runs on step '{call.get('step')}', which its sequence does not name"
            )
        if not served(str(call.get("argv") or "")):
            errors.append(
                f"processes/{name}/host_calls runs `thea {call.get('argv')}`, which the parser does not serve"
            )
        timeout = call.get("timeout_ms")
        if not isinstance(timeout, int) or timeout <= 0 or not str(call.get("event") or "").strip():
            errors.append(
                f"processes/{name}/host_calls `{call.get('argv')}` declares no event or no positive timeout_ms "
                "— a host call with no deadline hangs the turn it serves"
            )
    return errors


def companion_errors() -> list[str]:
    """A consumed call the parser no longer serves, or a driven process call the companion never declared."""
    errors = [
        f"companions/{r['id']} consumes `thea {c['argv']}`, which this release no longer serves — a verb or "
        "flag a companion reads was removed or renamed under it"
        for r in companions()
        for c in r["consumes"]
        if not c["present"]
    ]
    processes = atlas().get("processes") or {}
    for name, spec in processes.items():
        errors += host_call_errors(name, spec or {})
    for name, row in (atlas().get("companions") or {}).items():
        for process in row.get("drives") or []:
            if process not in processes:
                errors.append(
                    f"companions/{name} drives process {process}, which atlas.yaml/processes does not declare"
                )
            errors += [
                f"companions/{name} drives {process}, whose host_calls run `thea {argv}`, and its consumes "
                "does not declare it — the host would call what its contract never named"
                for argv in host_calls(process)
                if argv not in (row.get("consumes") or [])
            ]
    return errors


def record() -> dict:
    rows = companions()
    return {
        "schema": 1,
        "command": "links",
        "release": release(),
        "companions": rows,
        "missing": [f"{r['id']}: thea {c['argv']}" for r in rows for c in r["consumes"] if not c["present"]],
    }


def main(argv: list[str]) -> int:
    got = record()
    if "--json" in argv:
        print(json.dumps(got, indent=2))
    else:
        rel = got["release"]
        print(f"{rel['tag']}  {rel['repository']}")
        for row in got["companions"]:
            print(f"{row['id']}: reads {', '.join('thea ' + c['argv'] for c in row['consumes']) or 'nothing'}")
        for line in got["missing"]:
            print(f"MISSING  {line}: a companion reads a command this release no longer serves")
    return 1 if got["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
