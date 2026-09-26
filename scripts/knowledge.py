#!/usr/bin/env python3
"""Where a fact may live, how it is retrieved, and the asymmetries underneath both.

WHY (2.13.0). This repository was rigorous about code and silent about KNOWLEDGE. It said nothing
about which facts belong in a model's weights, which must be retrieved, and which are only ever
true for one session — so the default applied: everything becomes a document, everything gets
embedded, and a question with an exact answer is served by similarity. The cost of that is never a
visibly wrong answer. It is a PLAUSIBLE one: a row that exists is paraphrased, a row that does not
is invented, and the two are identical in the output.

THREE DECLARATIONS, EACH CHECKED BOTH WAYS. `data_classes` says how each class is retrieved and
the way it fails. `knowledge_layers` says what each layer must NEVER hold, because the defect is
always a volatile fact in the layer that cannot be updated. `retrieval_policy` says how something
is indexed, once, so it is not re-decided per ingestion — and every `never_*` list is the half
that does the work, since each one names the default that would otherwise win.

`asymmetries` is the layer under all of it: two words that belong together and are unequal. Almost
every rule in this tree is one of them, and naming the pair makes the rule portable.

WHAT THIS DOES NOT PROVE: that an index was BUILT this way. This checks the declaration is
complete and self-consistent; a retrieval system that ignores it is caught by the retrieval_change
gate, and by a citation a reader can open.
"""
from __future__ import annotations

import sys

from atlascore import ROOT, atlas, route_targets, strict_yaml, tracked


def _rows(name: str) -> dict:
    return atlas().get(name) or {}


def data_class_errors() -> list[str]:
    """Every class says how it is retrieved, what travels with it, and how it FAILS."""
    errors: list[str] = []
    classes = _rows("data_classes")
    policy = _rows("retrieval_policy")
    for name, spec in classes.items():
        for field in ("examples", "retrieval", "chunking", "required_metadata", "fails_by"):
            if not (spec or {}).get(field):
                errors.append(f"data_classes/{name} declares no {field} — a class with no named "
                              "failure mode is one whose failure will be read as an answer")
        chunking = str((spec or {}).get("chunking") or "")
        if chunking in {str(b) for b in policy.get("never_chunk_by") or []}:
            errors.append(f"data_classes/{name} chunks by '{chunking}', which retrieval_policy "
                          "names as a way never to chunk")
    if not classes:
        errors.append("atlas.yaml declares no data_classes, so every class gets the mechanism "
                      "whoever wrote the ingestion happened to know")
    sidecar = {str(f) for f in policy.get("sidecar_fields") or []}
    for name, spec in classes.items():
        if str(name) == "unstructured":
            missing = {str(f) for f in (spec or {}).get("required_metadata") or []} - sidecar
            if missing:
                errors.append(f"data_classes/unstructured requires {sorted(missing)}, which "
                              "retrieval_policy/sidecar_fields does not carry — a requirement "
                              "nothing writes is a requirement nothing checks")
    return errors


def knowledge_layer_errors() -> list[str]:
    """Each layer names what it must NEVER hold, and who closes it when it does."""
    errors: list[str] = []
    layers = _rows("knowledge_layers")
    for name, spec in layers.items():
        for field in ("holds", "never_holds", "staleness", "closed_by"):
            if not (spec or {}).get(field):
                errors.append(f"knowledge_layers/{name} declares no {field}")
        holds = {str(h) for h in (spec or {}).get("holds") or []}
        for other, other_spec in layers.items():
            if other == name:
                continue
            shared = holds & {str(h) for h in (other_spec or {}).get("holds") or []}
            if shared:
                errors.append(f"knowledge_layers/{name} and /{other} both hold {sorted(shared)} — "
                              "a fact in two layers is updated in one of them")
    if len(layers) < 2:
        errors.append("knowledge_layers needs at least the volatile and the durable, or the split "
                      "it exists to make is not being made")
    return errors


def retrieval_policy_errors() -> list[str]:
    """The `never_*` lists are the half that does the work: each names a default that would win."""
    errors: list[str] = []
    policy = _rows("retrieval_policy")
    for field in ("chunking", "never_chunk_by", "search", "search_rule",
                  "invalidation", "never_invalidate_by", "sidecar_fields", "citation_rule"):
        if not policy.get(field):
            errors.append(f"retrieval_policy declares no {field}")
    if len(policy.get("search") or []) < 2:
        errors.append("retrieval_policy/search names fewer than two methods — a dense-only index "
                      "cannot find an exact symbol and a keyword-only one cannot find a paraphrase, "
                      "and the questions that need each look the same")
    if str(policy.get("invalidation")) in {str(n) for n in policy.get("never_invalidate_by") or []}:
        errors.append("retrieval_policy invalidates by something it also forbids")
    return errors


def asymmetry_errors() -> list[str]:
    """A pair is two unequal words WITH a place it is applied, or it is an aphorism."""
    errors: list[str] = []
    for name, spec in _rows("asymmetries").items():
        pair = (spec or {}).get("pair") or []
        if len(pair) != 2 or pair[0] == pair[1]:
            errors.append(f"asymmetries/{name} is not a pair of two distinct terms")
        for field in ("why", "applied_at"):
            if not str((spec or {}).get(field) or "").strip():
                errors.append(f"asymmetries/{name} names no {field} — a pair with nowhere it is "
                              "applied is an aphorism, and this repository refuses those")
    if not _rows("asymmetries"):
        errors.append("atlas.yaml declares no asymmetries")
    return errors


def selection_errors() -> list[str]:
    """Every pack is reachable by a NEED, and every axis says when not to reach for it.

    A roster answers "what is supported" and never "what should I use", so a pack reachable only
    by already knowing its name is a pack nobody selects. Both directions: an unselectable pack,
    and an axis naming a pack that does not exist.
    """
    errors: list[str] = []
    axes = _rows("language_selection")
    targets = set(route_targets())
    covered: set[str] = set()
    for name, spec in axes.items():
        for field in ("need", "packs", "when_not", "maturity"):
            if not (spec or {}).get(field):
                errors.append(f"language_selection/{name} declares no {field} — an axis with no "
                              "'when_not' recommends itself for everything")
        for pack in (spec or {}).get("packs") or []:
            if str(pack) not in targets:
                errors.append(f"language_selection/{name} names pack '{pack}', which is not a route")
            covered.add(str(pack))
    for pack in sorted(targets - covered):
        errors.append(f"pack '{pack}' is in no language_selection axis, so it is reachable only by "
                      "already knowing its name — which is not selection, it is recall")
    return errors


def pick(axis: str | None) -> int:
    """`atlas pick [axis]` — which packs answer a need, and when not to reach for it."""
    axes = _rows("language_selection")
    if axis is None:
        for name, spec in axes.items():
            print(f"{name:<22} {', '.join(str(p) for p in (spec or {}).get('packs') or [])}")
            print(f"{'':<22} {(spec or {}).get('need')}")
        print(f"{len(axes)} axes over {len(route_targets())} packs; `atlas pick <axis>` for one")
        return 0
    spec = axes.get(str(axis))
    if not spec:
        print(f"unknown axis: {axis}")
        print("available: " + ", ".join(sorted(axes)))
        return 2
    print(f"{axis}: {spec.get('need')}")
    print(f"packs: {', '.join(str(p) for p in spec.get('packs') or [])}")
    print(f"maturity: {spec.get('maturity')}")
    print(f"DO NOT reach for this when: {spec.get('when_not')}")
    return 0


def baseline_errors() -> list[str]:
    """Every baseline row says WHY, and the never-by-default list is not empty.

    A baseline that only says what to add is a shopping list. The refusals are what stop an
    environment accreting, and an empty refusal list means nothing was ever weighed against
    anything — so it is a structural failure here, not a stylistic one.
    """
    errors: list[str] = []
    baseline = _rows("developer_baseline")
    if not baseline:
        return ["atlas.yaml declares no developer_baseline, so the answer to 'what do I need' is "
                "whatever the last tutorial installed"]
    for section in ("required", "recommended"):
        for name, spec in (baseline.get(section) or {}).items():
            reason = spec.get("why") if isinstance(spec, dict) else spec
            if not str(reason or "").strip():
                errors.append(f"developer_baseline/{section}/{name} states no reason, which makes "
                              "it a preference somebody will remove without knowing what it cost")
    if not (baseline.get("never_by_default") or {}):
        errors.append("developer_baseline names nothing to avoid, so it is a shopping list — and a "
                      "shopping list is how a workstation ends up with four linters that disagree")
    mcp = baseline.get("mcp") or {}
    for field in ("rule", "cost_nobody_counts", "review_trigger"):
        if not str(mcp.get(field) or "").strip():
            errors.append(f"developer_baseline/mcp declares no {field} — an enabled server is paid "
                          "for on every request, including the ones that never use it")
    return errors


def governance_errors() -> list[str]:
    """Every tier says what it means, how to test membership, and what happens at its edge — and
    every RATCHET in this tree is named by the bounded tier.

    The cross-check is the part that matters. A tier table nobody's bounds point at is a nice
    diagram; asserting that each declared ratchet appears in `bounded/here` is what makes the
    middle tier real, and it is what stopped a wall being worked around for a third time.
    """
    errors: list[str] = []
    tiers = _rows("governance_tiers")
    for name in ("hard", "bounded", "dynamic"):
        spec = tiers.get(name)
        if not isinstance(spec, dict):
            errors.append(f"governance_tiers declares no '{name}' tier, and the middle one is the point")
            continue
        for field in ("means", "test", "here", "on_breach"):
            if not (spec or {}).get(field):
                errors.append(f"governance_tiers/{name} declares no {field}")
    if "refuse" not in str((tiers.get("hard") or {}).get("on_breach") or ""):
        errors.append("governance_tiers/hard does not REFUSE at its edge, which makes it bounded")
    for field in ("adds_rule", "cuts_rule"):
        if not str((tiers.get("bounded") or {}).get(field) or "").strip():
            errors.append(f"governance_tiers/bounded declares no {field} — an envelope with no rule "
                          "for adds and cuts is a wall with a door and no lock")
    # EVERY RATCHET IS NAMED BY THE BOUNDED TIER, both ways, so a bound cannot exist untiered.
    bounded = " ".join(str(item) for item in (tiers.get("bounded") or {}).get("here") or [])
    policy = atlas().get("context_policy") or {}
    ratchets = ["entry_paths"] if policy.get("entry_paths") else []
    ratchets += ["install_footprint"] if policy.get("install_footprint") else []
    ratchets += ["example_coverage"] if policy.get("example_coverage") else []
    ratchets += ["code_shape"] if atlas().get("code_shape") else []
    for name in ratchets:
        if name not in bounded:
            errors.append(f"'{name}' is a ratchet and governance_tiers/bounded does not name it — "
                          "an untiered bound is one every reader gets to classify generously")
    return errors


def knowledge_errors() -> list[str]:
    return (data_class_errors() + knowledge_layer_errors()
            + retrieval_policy_errors() + asymmetry_errors() + selection_errors()
            + baseline_errors() + governance_errors())


def why(name: str | None) -> int:
    """`atlas why <id>` — the pair, the reason it is unequal, and where this tree applies it."""
    pairs = _rows("asymmetries")
    if name is None:
        for key, spec in sorted(pairs.items()):
            left, right = (spec or {}).get("pair") or ["?", "?"]
            print(f"{key:<26} {left}  <->  {right}")
        print(f"{len(pairs)} asymmetries; `atlas why <id>` for the reason and where it is applied")
        return 0
    spec = pairs.get(str(name))
    if not spec:
        print(f"unknown asymmetry: {name}")
        print("available: " + ", ".join(sorted(pairs)))
        return 2
    left, right = spec.get("pair") or ["?", "?"]
    print(f"{name}: {left}  <->  {right}")
    print(f"why unequal: {spec.get('why')}")
    print(f"applied here at: {spec.get('applied_at')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    classes, layers, policy = _rows("data_classes"), _rows("knowledge_layers"), _rows("retrieval_policy")
    for name, spec in classes.items():
        print(f"{name:<17} retrieved by {spec.get('retrieval')}")
        print(f"{'':<17} chunked {spec.get('chunking')}; fails by {spec.get('fails_by')}")
    for name, spec in layers.items():
        print(f"layer {name:<11} NEVER holds {spec.get('never_holds')}")
    print(f"index: chunk by {policy.get('chunking')}, invalidate by {policy.get('invalidation')}, "
          f"search {' + '.join(str(s) for s in policy.get('search') or [])}")
    print(f"corpus here: {sum(1 for p in tracked() if p.suffix.lower() == '.md')} documents under "
          f"{ROOT.name}, every one routed before it is read")
    problems = knowledge_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: the DECLARATION is complete and consistent. That an index was actually built")
    print("       this way is what the retrieval_change gate and an openable citation answer.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())


def decision_records() -> dict:
    """systems/decisions.yaml — read from the resolved atlas, never shipped, like all policy content."""
    path = ROOT / "systems" / "decisions.yaml"
    return (strict_yaml(path.read_text(encoding="utf-8"), str(path)) or {}) if path.is_file() else {}


def decide(name: str | None, as_json: bool) -> int:
    """`atlas decide [<id>]` — the decision, when to choose each option, the failure, the proof."""
    import json as _json
    records = decision_records()
    if name is None:
        for key, spec in sorted(records.items()):
            mark = "proven" if (spec or {}).get("proven_by") else "declared"
            print(f"{key:<30} {mark:<9} {(spec or {}).get('decides')}")
        print(f"{len(records)} decisions; `atlas decide <id>` for options, failure and proof")
        return 0
    spec = records.get(str(name))
    if not spec:
        print(f"unknown decision: {name}\navailable: {', '.join(sorted(records))}")
        return 2
    if as_json:
        print(_json.dumps({"schema": 1, "command": "decide", "atlas_version": str(atlas().get("version")),
                           "id": name, **spec}, indent=2))
        return 0
    print(f"{name}: {spec.get('decides')}")
    for option, when in (spec.get("choose_when") or {}).items():
        print(f"  {option:<24} {when}")
    print(f"failure:  {spec.get('failure_mode')}\nprove it: {spec.get('verified_by')}")
    print(f"proven by: {spec.get('proven_by') or 'nothing yet — declared, not exercised'}")
    print(f"source:   {spec.get('source')}" + ("" if spec.get("source_verified", True) else f"  (unverified: {spec.get('uncertain')})"))
    return 0


def failures(name: str | None, as_json: bool) -> int:
    """`thea failures [<id>]` — the ledger an agent learns from, without reading atlas.yaml (3.13.0).

    A reviewer called it the most original artifact here and found no way to see it but grepping YAML.
    Listing: every shape with its sightings and whether a program enforces it; an id prints the record."""
    import json as _json
    ledger = atlas().get("agent_failure_modes") or {}
    if as_json:
        print(_json.dumps({"schema": 1, "command": "failures", "atlas_version": str(atlas().get("version")),
                           "failures": ledger if name is None else {name: ledger.get(name)}}, indent=2))
        return 0 if name is None or name in ledger else 2
    if name is None:
        for key, spec in sorted(ledger.items(), key=lambda kv: -int((kv[1] or {}).get("sightings") or 0)):
            spec = spec or {}
            guard = "guarded" if spec.get("enforced_by") else "standing verdict"
            print(f"{int(spec.get('sightings') or 0):>3}x  {key:<58} {guard}")
        print(f"{len(ledger)} shapes, most-sighted first — `thea failures <id>` for one")
        return 0
    if name not in ledger:
        print(f"no failure mode '{name}' — `thea failures` lists them")
        return 2
    for field, value in (ledger[name] or {}).items():
        print(f"{field:>14}: {' '.join(str(value).split())}")
    return 0


# --- landing-page blocks, rendered by atlasgen from declarations (3.12.0-3.13.0) ---
def gate_example_block() -> str:
    """A real `gate` answer for a real file in this tree, regenerated every build, so the example the
    landing page shows is the command's output today and never a transcript that aged."""
    import shlex  # noqa: PLC0415

    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415
    path = "scripts/doctor.py"
    rows = [gate_record(path, g) for g in required_gates({"change_class": "source_change"})]
    body = [f"{n}. {r['gate']}: " + (shlex.join(r["argv"]) if r["argv"] else f"{r['state']} — {r['why']}")
            for n, r in enumerate(rows, 1)]
    return "```console\n$ thea gate " + path + "\n" + "\n".join(body) + "\n```"


def glance_block() -> str:
    """The headline figures, computed on every build: what a reader should know in one line (3.13.0)."""
    from contextcost import footprint  # noqa: PLC0415
    a = atlas()
    routes = len(route_targets())
    gates = len(a.get("gate_tools") or {})
    runtimes = len(a.get("runtime_entry") or [])
    return (f"**{routes}** languages · **{len(a.get('artifact_routes') or {})}** extensions · "
            f"**{gates}** gates · **{runtimes}** runtimes · "
            f"**{len(a.get('agent_failure_modes') or {})}** failure shapes · "
            f"**{len(a.get('hard_invariants') or [])}** invariants · "
            f"**{len(a.get('instruments') or {})}** instruments · "
            f"**{footprint()['dependencies']}** dependency")


def settings_block() -> str:
    """What Thea does in each setting, rendered from first_sweep/settings: one declaration feeds CHAT.md
    and the landing page, so "who is this for" is answered by the contract and cannot drift from it."""
    rows = ["| where you use it | what Thea does there |", "|---|---|"]
    for setting, what in ((atlas().get("first_sweep") or {}).get("settings") or {}).items():
        rows.append(f"| {setting[0].upper() + setting[1:]} | {' '.join(str(what).split())} |")
    return "\n".join(rows)


# Named, not built from an f-string: a caller a text search can see (orphans.py found the indirection).
README_BLOCKS = {"gate-example": gate_example_block, "settings": settings_block, "glance": glance_block}


def steps(path_value: str, runtime: str, change: str, as_json: bool) -> int:
    """`thea steps <path> --runtime <id>` — the ordered implementation plan for ONE runtime (3.14.0).

    `plan` answers which gates; this answers what to do, in order, from where this runtime stands: how it
    reaches Thea, what to load, the commands that prove the change, the budget, the sandbox an autonomous
    run needs, the done check, and where the work RETURNS — a pull request for an agent, a checklist and
    the report verb for a chat. Every line is read from a declaration; nothing here is typed per runtime."""
    import json as _json

    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415
    from atlascore import route_for  # noqa: PLC0415
    a = atlas()
    entry = {str(e["id"]): e for e in a.get("runtime_entry") or []}
    if runtime not in entry:
        print(f"unknown runtime '{runtime}' — one of: {', '.join(entry)}")
        return 2
    route = route_for(path_value)
    via = ((a.get("native_agent_tools") or {}).get("runtimes") or {}).get(runtime, {}).get("thea_via") or []
    runs = bool(via)
    gates = [gate_record(path_value, g) for g in required_gates({"change_class": change})] if route else []
    budget = (a.get("agent_policy") or {}).get("default_budgets") or {}
    plan = [f"reach Thea through {', '.join(via) or 'the page itself: ' + str(entry[runtime]['loads'])}",
            f"route {path_value}: " + (f"pack {route} — load languages/{route}/ only" if route else "no route; refuse, do not guess"),
            *[f"prove with {g['gate']}: " + (__import__("shlex").join(g["argv"]) if g["argv"] else f"{g['state']} — {g['why']}") for g in gates],
            f"stay inside the budget: {', '.join(f'{k} {v}' for k, v in budget.items())}"]
    plan += (["autonomous? isolate it: python scripts/sandboxgen.py docker <contract>",
              "done only when: python scripts/verify.py exits 0",
              "return: python scripts/branchstate.py --land — a pull request, never a bare push"] if runs else
             ["return: the gate checklist above with each claim labelled; file any gap in Thea with the report verb"])
    if as_json:
        print(_json.dumps({"schema": 1, "command": "steps", "runtime": runtime, "path": path_value, "route": route,
                           "change_class": change, "steps": plan}, indent=2))
    else:
        print("\n".join(f"{n}. {s}" for n, s in enumerate(plan, 1)))
    return 0 if route else 2

