"""`thea links`: where this release is, and what each companion reads from it. Read-only.

TheaOS and the Thea site both depend on this repository and used to carry their own copy of
what they depend on: a release tag typed into a download link, a command list typed into a panel table.
Both drifted (a site pinned to the previous tag; a TheaOS page waiting for a command that had shipped).
This record is the one place that states it, from `atlas.yaml/companions` and the declared identity.

Every command a companion consumes is checked against the parser that serves it: a row naming a command
that is gone reports `present: false` and the exit is 1. The record names no companion's repository: the
public tree carries only what a reader outside the owner can use.
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


def command_names() -> set[str]:
    from commands import COMMAND_ROWS

    return {name for name, *_ in COMMAND_ROWS}


def companions() -> list[dict]:
    """One row per declared companion, each consumed command read back against the parser."""
    served = command_names()
    rows = []
    for name, row in (atlas().get("companions") or {}).items():
        consumes = [{"argv": argv, "present": argv.split()[0] in served} for argv in row.get("consumes") or []]
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
