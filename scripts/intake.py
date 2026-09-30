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

HOW PEOPLE ACTUALLY WRITE (3.47.0), declared in atlas.yaml/prompt_policy:
  open list   "x, y, etc" / "and more" / "and so on" — the named items are EXAMPLES of a class. The class a
              declared roster shares with them is expanded and stated as the scope; with no roster, the
              items are the floor and the ask is to name the class. Never narrowed to the examples silently.
  read as     a word one edit from a declared name ("teha", "evrify") is echoed back as that name — shown,
              never rewritten silently, so a wrong reading is caught in one line.
  strategic   "should we", "options", "brainstorm" — a decision, not an edit: routed to `thea brainstorm --new`.
"""
from __future__ import annotations

import json
import re
import sys

from atlascore import ROOT, atlas, route_for

DONE_WORDS = r"\b(so that|until|should|must|passes?|pass|green|returns?|expect|test)\b"


def _stems(words: set[str]) -> set[str]:
    return {w[:5] for w in words if len(w) > 3}


def rosters() -> dict[str, list[str]]:
    """The declared classes an open list can belong to — names an agent could mean, each from its one declaration."""
    from atlascore import route_targets  # noqa: PLC0415
    from commands import build_parser  # noqa: PLC0415
    a = atlas()
    return {"runtimes": [str(r.get("id")) for r in a.get("runtime_entry") or []],
            "languages": list(route_targets()), "processes": list(a.get("processes") or {}),
            "commands": list(build_parser()[1].choices), "tiers": list(a.get("stack_tiers") or {}),
            "change classes": list((a.get("verification_policy") or {}).get("profiles") or {})}


def open_lists(prompt: str) -> list[dict]:
    """Each "a, b, etc" in the prompt: its named items, the declared class they belong to, and that class's members."""
    policy = atlas().get("prompt_policy") or {}
    marker = "|".join(re.escape(str(m)) for m in policy.get("open_list_markers") or ["etc"])
    found = []
    for hit in re.finditer(rf"([^.;:!?\n]{{3,120}}?)[,\s]+(?:{marker})(?=[\s.,;:!?)]|$)", prompt, re.I):
        items = [w.strip().lower() for w in re.split(r",|\band\b|\bor\b|/", hit.group(1)) if w.strip()][-6:]
        items = [i.split()[-1] for i in items if i.split()]
        def parts(members: list[str]) -> set[str]:  # `openai_codex` answers to codex; `quantum/qsharp` to qsharp
            return {p for m in members for p in [m.lower(), *re.split(r"[_/ -]", m.lower())] if p}
        classes = {name: members for name, members in rosters().items() if set(items) & parts(members)}
        best = max(classes, key=lambda c: len(set(items) & parts(classes[c])), default=None)
        found.append({"items": items, "class": best,
                      "scope": sorted(dict.fromkeys(m for m in classes[best] if m)) if best else items,
                      "reading": (f"examples of {best}: the scope is all {len(set(classes[best]))} declared" if best else
                                  "examples of an undeclared class: the named items are the floor — name the class if it matters")})
    return found


def _one_edit(a: str, b: str) -> bool:
    """One substitution, insertion, deletion or adjacent swap apart — the typos fast typing makes."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [k for k in range(len(a)) if a[k] != b[k]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    short, long_ = sorted((a, b), key=len)
    return any(long_[:k] + long_[k + 1:] == short for k in range(len(long_)))


def read_as(prompt: str) -> dict[str, str]:
    """Words one edit from a declared name, echoed back as that name — never rewritten silently."""
    vocab = {v.lower() for members in rosters().values() for v in members if v and len(v) > 3} | {"thea", "atlas"}
    out = {}
    for word in dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z-]{3,}", prompt)):
        low = word.lower()
        near = [v for v in vocab if _one_edit(low, v) and low.rstrip("s") != v.rstrip("s")] if low not in vocab else []
        if len(near) == 1:  # two candidates is ambiguity: echo nothing rather than guess
            out[word] = near[0]
    return out


def strategic(prompt: str) -> bool:
    words = (atlas().get("prompt_policy") or {}).get("strategic_markers") or []
    return any(re.search(rf"\b{re.escape(str(w))}\b", prompt, re.I) for w in words)


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
    decision = strategic(prompt) and not files
    if not files and not decision:
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
            "open_lists": open_lists(prompt), "read_as": read_as(prompt),
            "process": "strategic_brainstorm" if decision else None,
            "next": (f"thea brainstorm --new {json.dumps(prompt[:120])}" if decision else
                     f"thea steps {files[0]['path']} --change {change}" if files and not questions
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
        for word, name in record["read_as"].items():
            print(f"read as   {word} -> {name}")
        for lst in record["open_lists"]:
            print(f"open list {', '.join(lst['items'])}, etc -> {lst['reading']}: {', '.join(lst['scope'][:12])}")
        print("\n".join(f"ASK       {q}" for q in record["questions"]) or "ready     every slot is resolved")
        print(f"next      {record['next']}")
    return 0 if not record["questions"] else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
