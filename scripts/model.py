"""`thea model` — which rung answers each typed judgment, read from the attached student bundle.

    thea model [--to dashboard|repo|DIR]          status lines; exit 0 when the bundle verifies and is current
    thea model --json [--to ...]                  the schema 1 record the Thea Dashboard's Model page parses

THE RUNGS. A judgment in systems/judgments.yaml is answered on one of three rungs:
  rules    the caller brings the answer and p, and declared facts decide; nothing is called;
  teacher  a keyed model the caller runs, whose answer and p `thea judge` then holds to the bar;
  student  a micro pack answered here, in-process, by the vendored stdlib loader (modelpack.py): no key, no port.
The bundle's manifest names each judgment's rung; a promotion to student retires the key the teacher needed, and
the manifest names that key. Nothing here installs or needs a key: the student is keyless, and an install with no
bundle attached answers every judgment on its old rung.

Where the bundle is: --to, else ./.thea/model when one is attached there, else the dashboard's model folder. A bundle
answers only when every sha256 matches its manifest; each pack answers only while its judgment's record in the
judgments.yaml this tree holds is the contract it was trained on, so an edited judgment is NOT RUN alone. Exit 0 OK, 1 NOT RUN, so the exit code is the verdict whether or not --json is asked for.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import modelpack

JUDGMENTS = Path("systems") / "judgments.yaml"


def target_dir(name: str | None) -> Path:
    if name == "dashboard":
        return modelpack.DASHBOARD
    if name == "repo":
        return Path.cwd() / modelpack.REPO_DIR
    if name:
        return Path(name).expanduser()
    repo = Path.cwd() / modelpack.REPO_DIR
    return repo if (repo / "current").is_symlink() else modelpack.DASHBOARD


def judgments_text() -> str | None:
    """The text of the judgments.yaml `thea judge` reads; None when this tree has none (a NOT RUN reason)."""
    from atlascore import ROOT  # noqa: PLC0415

    try:
        return (ROOT / JUDGMENTS).read_text(encoding="utf-8")
    except OSError:
        return None


def student(jid: str, state: str, to: str | None = None, text: str | None = None) -> dict:
    """The student's answer for one judgment: {answer, p, rung: student, bundle}, or {verdict: NOT RUN, why, rung}
    where rung is the one the manifest declares (None when no bundle verifies), so the caller can fall back to it."""
    target = target_dir(to)
    text = judgments_text() if text is None else text
    st = modelpack.status(target, text)
    why = st["not_run"].get("_bundle") or st["not_run"].get(jid)
    if why:
        return {**modelpack.not_run(why.removeprefix("NOT RUN: ")), "rung": None}
    entry = st["manifest"]["packs"].get(jid)
    if not entry:
        return {**modelpack.not_run(f"the bundle at {target} has no pack for {jid}"), "rung": None}
    if entry["rung"] != "student":
        return {**modelpack.not_run(f"the manifest puts {jid} on the {entry['rung']} rung"), "rung": entry["rung"]}
    got = modelpack.decide(target, state, [jid], cast(str, text))
    if got[jid].get("verdict") == "NOT RUN":
        return {**got[jid], "rung": "student"}
    return {"answer": got[jid]["answer"], "p": got[jid]["p"], "rung": "student", "bundle": got["_meta"]["backend"]}


def main(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="thea model", description=cast(str, __doc__).splitlines()[0])
    parser.add_argument("--to", default=None, help="dashboard | repo | DIR")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    st = modelpack.status(target_dir(args.to), judgments_text())
    if args.json:  # one record on stdout and nothing else: the dashboard parses the whole of it
        print(json.dumps(modelpack.model_record(st), sort_keys=True))
    else:
        print("\n".join(modelpack.status_lines(st)))
    return 1 if st["not_run"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
