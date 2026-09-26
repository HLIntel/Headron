#!/usr/bin/env python3
"""A user's prompt, digested into a task — or into the questions that make it one. Never a guess.

WHY (3.20.0). Thea answered well for an agent that already knew the file, the change class and what done
means. A real prompt rarely says all three ("make the retry thing better"), and a model handed a vague ask
fills the gaps with invention — which is where most wasted runs and wrong fixes start. This reads the
prompt against the declarations and returns what it can resolve (files and their routes, a role, a change
class) and, for each slot it cannot, one plain question. The research is consistent across models: an
explicit goal, the target, and an acceptance test raise completion more than any phrasing trick — so
those are the three slots, and a missing one is asked for, never assumed.

  thea intake "<prompt>" [--json]
"""
from __future__ import annotations

import json
import re
import sys

from atlascore import ROOT, atlas, route_for

DONE_WORDS = r"\b(so that|until|should|must|passes?|pass|green|returns?|expect|test)\b"


def _stems(words: set[str]) -> set[str]:
    return {w[:5] for w in words if len(w) > 3}


def digest(prompt: str) -> dict:
    a = atlas()
    words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z_-]+", prompt)}
    stems = _stems(words)
    paths = [p for p in re.findall(r"[\w./-]+\.[A-Za-z0-9]+", prompt) if (ROOT / p).exists() or route_for(p)]
    files = [{"path": p, "route": route_for(p)} for p in dict.fromkeys(paths)]
    classes = [c for c in (a.get("verification_policy") or {}).get("profiles") or {}
               if c != "source_change" and _stems(set(c.split("_"))) & stems]
    roles = [r for r in (a.get("agent_roles") or {}) if r[:5] in stems or r[:-2][:5] in stems]
    # ASK ONLY WHAT BLOCKS ACTION (owner, 3.20.0): the goal is shipped code, not an interview. A missing
    # acceptance becomes the file's own gates, stated; two plausible classes run BOTH sets of gates — the
    # stricter union — rather than stopping to ask. Only no target, or no stated change, stops the work.
    questions = []
    if not files:
        questions.append("Which file or directory is this about?")
    if len(words) < 4:
        questions.append("What should change, in one sentence?")
    from agentpolicy import required_gates  # noqa: PLC0415
    change = classes[0] if len(classes) == 1 else "source_change"
    gates = sorted({g for c in (classes or ["source_change"]) for g in required_gates({"change_class": c})})
    acceptance = ("as the prompt states" if re.search(DONE_WORDS, prompt, re.I)
                  else "assumed: every gate below passes for each file — say so if done means more")
    return {"schema": 1, "command": "intake", "role": roles[0] if len(roles) == 1 else "implementer",
            "change_class": change, "change_class_basis": "named in the prompt" if len(classes) == 1 else
            f"several named — running the union of {', '.join(classes)}" if classes else
            "the default for a code change — say so if it touches an API, dependency or security",
            "files": files, "gates": gates, "acceptance": acceptance, "questions": questions,
            "next": (f"thea steps {files[0]['path']} --change {change}" if files and not questions
                     else "answer the questions above before any edit")}


def main(argv: list[str]) -> int:
    text = " ".join(a for a in argv if a != "--json")
    record = digest(text)
    if "--json" in argv:
        print(json.dumps(record, indent=2))
    else:
        for f in record["files"]:
            print(f"file      {f['path']} -> {f['route'] or 'no route: refused, not guessed'}")
        print(f"role      {record['role']}\nchange    {record['change_class']} ({record['change_class_basis']})")
        print(f"gates     {', '.join(record['gates'])}\ndone      {record['acceptance']}")
        print("\n".join(f"ASK       {q}" for q in record["questions"]) or "ready     every slot is resolved")
        print(f"next      {record['next']}")
    return 0 if not record["questions"] else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
