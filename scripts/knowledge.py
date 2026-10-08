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


EDGE_FIELDS = ("from", "to", "examples", "plan", "applied_by", "gate", "proves", "does_not_prove", "closed_by")


def artifact_edge_errors() -> list[str]:
    """Every edge joins two declared classes, is applied by something other than the model, and names its gate."""
    import re  # noqa: PLC0415
    edges, classes, gates = _rows("artifact_edges"), _rows("data_classes"), _rows("gate_tools")
    if not edges:
        return ["atlas.yaml declares no artifact_edges, so every non-code task is a format-specific agent"]
    errors: list[str] = []
    for name, spec in edges.items():
        spec = spec or {}
        errors += [f"artifact_edges/{name} declares no {f}" for f in EDGE_FIELDS if not spec.get(f)]
        errors += [f"artifact_edges/{name} names class '{c}', which data_classes does not declare"
                   for c in [*(spec.get("from") or []), *(spec.get("to") or [])] if str(c) not in classes]
        if spec.get("gate") and str(spec["gate"]) not in gates:
            errors.append(f"artifact_edges/{name} is proven by gate '{spec['gate']}', which gate_tools does not hold")
        if re.search(r"\b(model|llm|agent)\b", str(spec.get("applied_by") or ""), re.IGNORECASE):
            errors.append(f"artifact_edges/{name} is applied by a model — the model writes the plan and a "
                          "deterministic step applies it, or the model grades its own work")
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
    return (data_class_errors() + artifact_edge_errors() + knowledge_layer_errors()
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


def system_records(stem: str) -> dict:
    """systems/<stem>.yaml — read from the resolved atlas, never shipped, like all policy content."""
    path = ROOT / "systems" / f"{stem}.yaml"
    return (strict_yaml(path.read_text(encoding="utf-8"), str(path)) or {}) if path.is_file() else {}


def decision_records() -> dict:
    return system_records("decisions")


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
        print(_json.dumps({"schema": 1, "command": "decide", "atlas_version": str(atlas().get("version")), "id": name,
                           **spec, "lessons": lessons_for(f"{spec.get('decides')} {spec.get('failure_mode')}")}, indent=2))
        return 0
    print(f"{name}: {spec.get('decides')}")
    for option, when in (spec.get("choose_when") or {}).items():
        print(f"  {option:<24} {when}")
    print(f"failure:  {spec.get('failure_mode')}\nprove it: {spec.get('verified_by')}")
    print_lessons(f"{spec.get('decides')} {spec.get('failure_mode')}")  # the ledger at the design decision
    print(f"proven by: {spec.get('proven_by') or 'nothing yet — declared, not exercised'}")
    print(f"source:   {spec.get('source')}" + ("" if spec.get("source_verified", True) else f"  (unverified: {spec.get('uncertain')})"))
    for field, value in (spec.get("evidence") or {}).items():  # 3.21.0: the data, the trend, who pays
        print(f"{field + ':':<9} {value}")
    return 0


_LESSON_STOP = frozenset("the and for with that this from into when what which a an of to in on is it its not or by as at be are was".split())


def _words(text: str) -> set[str]:
    import re as _re
    return {w for w in _re.split(r"[^a-z0-9]+", str(text).lower()) if len(w) > 2 and w not in _LESSON_STOP}


# The two sides of one ledger: where each lives, which fields carry its words, and what breaks a tie.
LEDGERS = {
    "failures": ("agent_failure_modes", ("shape", "tell", "looks_like", "prevented_by"), "sightings"),
    "successes": ("agent_success_patterns", ("move", "when", "verification", "evidence"), "reused"),
}


def relevant(kind: str, query: str, limit: int = 3) -> list[tuple[str, int]]:
    """The entries of one side of the ledger most relevant to a file or task — `failures` or `successes`.

    Reading the whole ledger teaches everything at once and so, in practice, nothing. Ranked by shared
    words (an id word counts double), then by the ledger's weight; an entry sharing nothing is never
    returned, so a miss says `none` rather than padding."""
    name, fields, weight = LEDGERS[kind]
    return _ranked(atlas().get(name) or {}, fields, weight, query, limit)


def moves_for(failure: str) -> list[tuple[str, dict]]:
    """Every success that answers a failure: the move to make INSTEAD, wired by the success's `pairs`."""
    return [(key, spec or {}) for key, spec in (atlas().get("agent_success_patterns") or {}).items()
            if failure in ((spec or {}).get("pairs") or [])]


RECURRING = 2  # the second sighting is a rule (doctrine), so it names the move that replaces it


def success_wiring_errors() -> list[str]:
    """successes_answer_recurring_failures — the ledger is a graph: failure -> move -> guard (3.43.0).

    A failure record teaches what to avoid; seen twice, it has proven that avoiding is not enough and
    the replacing MOVE must be written down where an agent reads it. Each success carries the ATS fields an
    agent reuses as a step (move, when, verification), names the failures it answers, and names functions
    in this tree that prove it — so a success cannot be a slogan, and a pairing cannot dangle.
    """
    from agentpolicy import _resolves  # noqa: PLC0415
    failures = atlas().get("agent_failure_modes") or {}
    successes = atlas().get("agent_success_patterns") or {}
    errors: list[str] = []
    if not successes:
        return ["atlas.yaml declares no agent_success_patterns, so a failure says what went wrong and nothing says what to do"]
    for name, spec in successes.items():
        spec = spec or {}
        errors += [f"agent_success_patterns/{name} has no `{f}`" for f in ("move", "when", "verification", "pairs", "proven_by")
                   if not spec.get(f)]
        errors += [f"agent_success_patterns/{name} pairs '{p}', which agent_failure_modes does not hold"
                   for p in spec.get("pairs") or [] if p not in failures]
        errors += [f"agent_success_patterns/{name} is proven_by {r}, which is not in this tree"
                   for r in (str(r) for r in spec.get("proven_by") or []) if not _resolves(r)]
    errors += success_kind_errors(failures, successes)
    answered = {p for s in successes.values() for p in (s or {}).get("pairs") or []}
    errors += [f"agent_failure_modes/{name} is sighted {int((spec or {}).get('sightings') or 0)} times and no success "
               "names the move that replaces it — add one to agent_success_patterns with `pairs` naming it"
               for name, spec in failures.items()
               if int((spec or {}).get("sightings") or 0) >= RECURRING and name not in answered]
    return errors


def success_kind_errors(failures: dict, successes: dict) -> list[str]:
    """A success is a MOVE worth repeating, and each kind it claims is CHECKED (3.45.0): `reusable` names no
    single file in its `when`; `frameworkable` is proven by a function that also enforces a failure it pairs;
    `ai_beneficial` answers a failure with a tell. An entry that opens like an accomplishment is refused."""
    import re  # noqa: PLC0415
    declared = set(atlas().get("success_kinds") or {})
    verbs = {str(v).lower() for v in atlas().get("not_a_success") or []}
    errors: list[str] = []
    for name, spec in successes.items():
        spec = spec or {}
        kinds = [str(k) for k in spec.get("kinds") or []]
        first = str(spec.get("move") or "").split(" ", 1)[0].strip("`*").lower()
        pairs = [failures.get(p) or {} for p in spec.get("pairs") or []]
        errors += [f"agent_success_patterns/{name} opens with '{first}' — an accomplishment, not a move to repeat"] if first in verbs else []
        errors += [f"agent_success_patterns/{name} declares no kinds (atlas.yaml/success_kinds)"] if not kinds else []
        errors += [f"agent_success_patterns/{name} claims kind '{k}', which success_kinds does not declare" for k in kinds if k not in declared]
        if "reusable" in kinds and re.search(r"[\w-]+/[\w./-]+\.\w+", str(spec.get("when") or "")):
            errors.append(f"agent_success_patterns/{name} claims reusable but its `when` names one file")
        enforcers = {str(r) for f in pairs for r in f.get("enforced_by") or []}
        if "frameworkable" in kinds and not enforcers & {str(r) for r in spec.get("proven_by") or []}:
            errors.append(f"agent_success_patterns/{name} claims frameworkable but no proven_by also enforces a failure it pairs")
        if "ai_beneficial" in kinds and not any(f.get("tell") for f in pairs):
            errors.append(f"agent_success_patterns/{name} claims ai_beneficial but answers no failure with a tell")
    return errors


def lessons_for(query: str, limit: int = 2) -> list[dict]:
    """The ledger at the point of design (3.44.0): the shapes a file, language, task or decision shares words
    with, each as the one line an agent recognises it by and the move that replaces it. `route`, `learn`,
    `plan`, `decide` and every place page hand these over, so the lesson reaches the work that would repeat it."""
    ledger = atlas().get("agent_failure_modes") or {}
    # A SHAPE WHOSE GUARD LIVES IN THIS FILE IS ITS LESSON; one shared word is noise, two is a match.
    stem = str(query).rsplit("/", 1)[-1].split(".", 1)[0] if "/" in str(query) or "." in str(query) else ""
    owned = [k for k, s in ledger.items() if stem and any(str(r).split(".", 1)[0] == stem for r in (s or {}).get("enforced_by") or [])]
    picked = list(dict.fromkeys([*owned, *(k for k, score in relevant("failures", query, limit * 3) if score >= 2)]))[:limit]
    return [{"failure": key, "tell": " ".join(str((ledger.get(key) or {}).get("tell") or "").split()),
             "do": next((" ".join(str(m.get("move") or "").split()) for _, m in moves_for(key)), None)}
            for key in picked]


def print_lessons(query: str, limit: int = 2) -> None:
    """The text rendering of `lessons_for`, one shape per line and its move beneath it."""
    for lesson in lessons_for(query, limit):
        print(f"lesson {lesson['failure']}: {lesson['tell']}" + (f"\n  do: {lesson['do']}" if lesson["do"] else ""))


def _ranked(ledger: dict, fields: tuple, weight: str, query: str, limit: int) -> list[tuple[str, int]]:
    """Ledger entries sharing words with a query, most shared first (an id word counts double), then by weight."""
    # A PATH'S LEADING DIRECTORIES ARE WHERE IT LIVES, NOT WHAT IT IS: a home or checkout prefix shares words with
    # nothing it teaches. Only the last two components carry meaning; a task has no slash and is kept whole.
    q = _words("/".join(str(query).split("/")[-2:]) if "/" in str(query) else query)
    suffix = "." + str(query).rsplit(".", 1)[-1] if "." in str(query) else ""
    route = (atlas().get("artifact_routes") or {}).get(suffix)
    if route:
        q |= _words(route)
    scored = []
    for key, spec in ledger.items():
        spec = spec or {}
        body = _words(" ".join(str(spec.get(f) or "") for f in fields))
        score = 2 * len(q & _words(key)) + len(q & body)
        if score:
            scored.append((key, score, int(spec.get(weight) or 0)))
    scored.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return [(k, sc) for k, sc, _ in scored[:max(1, limit)]]


def failures_matching(text: str, as_json: bool) -> int:
    """`thea failures --match TEXT` — which declared shapes an error text is, by atlas.yaml/agent_failure_modes signature.

    Reads the one declaration dashboard callers and the model lab used to keep their own copy of."""
    import json as _json
    import re as _re

    ledger = atlas().get("agent_failure_modes") or {}
    hits = {
        key: spec
        for key, spec in ledger.items()
        if any(_re.search(pattern, text) for pattern in (spec or {}).get("signature") or [])
    }
    if as_json:
        print(_json.dumps({"schema": 1, "command": "failures", "atlas_version": str(atlas().get("version")),
                           "match": True, "failures": hits}, indent=2))
    elif not hits:
        print("no declared signature matches that text — `thea failures` lists the shapes; `--draft` files a new one")
    for key in hits if not as_json else ():
        print(f"{key} ({int(hits[key].get('sightings') or 0)}x)")
        print(f"  tell:    {' '.join(str(hits[key].get('tell') or '').split())}")
        for sid, move in moves_for(key):
            print(f"  do:      {' '.join(str(move.get('move') or '').split())} ({sid})")
    return 0 if hits else 1


def failures(name: str | None, as_json: bool, for_: str | None = None, limit: int = 3) -> int:
    """`thea failures [<id>]` — the ledger an agent learns from, without reading atlas.yaml (3.13.0).

    A reviewer called it the most original artifact here and found no way to see it but grepping YAML.
    Listing: every shape with its sightings and whether a program enforces it; an id prints the record."""
    import json as _json
    ledger = atlas().get("agent_failure_modes") or {}
    if for_:
        picked = [(lesson["failure"], 0) for lesson in lessons_for(for_, limit)]
        if as_json:
            print(_json.dumps({"schema": 1, "command": "failures", "atlas_version": str(atlas().get("version")),
                               "for": for_, "failures": {k: ledger[k] for k, _ in picked},
                               "moves": {k: {s: m.get("move") for s, m in moves_for(k)} for k, _ in picked}}, indent=2))
            return 0
        if not picked:
            print(f"none — no recorded shape shares a word with {for_!r}")
            return 0
        for key, _ in picked:
            spec = ledger[key] or {}
            print(f"{key} ({int(spec.get('sightings') or 0)}x)")
            print(f"  tell:    {' '.join(str(spec.get('tell') or '').split())}")
            print(f"  prevent: {' '.join(str(spec.get('prevented_by') or '').split())}")
            for sid, move in moves_for(key):
                print(f"  do:      {' '.join(str(move.get('move') or '').split())} ({sid})")
        return 0
    if as_json:
        print(_json.dumps({"schema": 1, "command": "failures", "atlas_version": str(atlas().get("version")),
                           "failures": ledger if name is None else {name: ledger.get(name)}}, indent=2))
        return 0 if name is None or name in ledger else 2
    if name is None:
        for key, spec in sorted(ledger.items(), key=lambda kv: -int((kv[1] or {}).get("sightings") or 0)):
            spec = spec or {}
            guard = "guarded" if spec.get("enforced_by") else "standing verdict"
            answer = f" · do: {moves_for(key)[0][0]}" if moves_for(key) else ""
            print(f"{int(spec.get('sightings') or 0):>3}x  {key:<58} {guard}{answer}")
        print(f"{len(ledger)} shapes, most-sighted first — `thea failures <id>` for one, `thea successes` for the moves")
        return 0
    if name not in ledger:
        print(f"no failure mode '{name}' — `thea failures` lists them")
        return 2
    for field, value in (ledger[name] or {}).items():
        print(f"{field:>14}: {' '.join(str(value).split())}")
    return 0


def draft(name: str, what: str, as_json: bool) -> int:
    """`thea failures <id> --draft "<what happened>"` — the ledger entry, prepared, never written (3.50.0).

    An agent that hits a mistake mid-task records it only when recording is one command. A known id gets
    its tell and the bump; a new id gets the nearest shapes (it may be one of them) and a `safeedit.py
    entry` line whose blank fields `check` refuses until filled — the id is the agent's, never invented."""
    import json as _json
    import re as _re
    import shlex as _shlex
    ledger = atlas().get("agent_failure_modes") or {}
    if not _re.fullmatch(r"an?_[a-z0-9_]+", name):
        print(f"refused: {name!r} is not a ledger id — name the shape as `a_<shape>` or `an_<shape>`")
        return 2
    known = ledger.get(name)
    nearest = [k for k, _ in relevant("failures", what, 3) if k != name]
    fields = (f"looks_like={what}", "sightings=1", f"intake={atlas().get('version')}",
              "shape=", "tell=", "prevented_by=", "unenforceable=", "closed_by=")
    command = None if known is not None else " ".join(_shlex.quote(x) for x in (
        "python", "scripts/safeedit.py", "entry", "atlas.yaml", "agent_failure_modes", name, *fields))
    if as_json:
        print(_json.dumps({"schema": 1, "command": "failures", "atlas_version": str(atlas().get("version")),
                           "failures": {name: known}, "draft": {"id": name, "known": known is not None,
                           "nearest": nearest, "command": command}}, indent=2))
        return 0
    if known is not None:
        seen = int((known or {}).get("sightings") or 0)
        print(f"{name} is recorded ({seen}x): bump `sightings: {seen}` to {seen + 1} in atlas.yaml")
        print(f"  tell:    {' '.join(str((known or {}).get('tell') or '').split())}")
        if seen + 1 >= 2 and not (known or {}).get("enforced_by"):
            print("  second sighting is a rule: name its guard in `enforced_by`, with a planted defect")
        return 0
    for key in nearest:
        print(f"nearest: {key} — `thea failures {key} --draft ...` if this is that shape again")
    print(command)
    print("fill every blank field; `thea check` refuses the entry until shape, tell, prevented_by and a closer are named")
    return 0


def successes(name: str | None, as_json: bool, for_: str | None = None, limit: int = 3) -> int:
    """`thea successes [<id>] [--for <file|task>]` — the moves that replaced recorded failures (3.43.0).

    A failure says what went wrong; its paired success says what to do instead, when, and how to prove it
    was done — the same fields an ATS task carries (move, when, verification). Each success names the
    failures it answers and the functions that prove it, so the two ledgers are one wired graph:
    failure -> move -> guard. JSON is the record an agent or another tool consumes."""
    import json as _json
    ledger = atlas().get("agent_success_patterns") or {}
    keys = ([k for k, _ in relevant("successes", for_, limit)] if for_ else
            [name] if name else sorted(ledger, key=lambda k: -int((ledger[k] or {}).get("reused") or 0)))
    if name and name not in ledger:
        print(f"no success pattern '{name}' — `thea successes` lists them")
        return 2
    if as_json:
        print(_json.dumps({"schema": 1, "command": "successes", "atlas_version": str(atlas().get("version")),
                           **({"for": for_} if for_ else {}), "successes": {k: ledger[k] for k in keys}}, indent=2))
        return 0
    if for_ and not keys:
        print(f"none — no recorded move shares a word with {for_!r}")
    for key in keys:
        spec = ledger[key] or {}
        print(f"{key} ({int(spec.get('reused') or 0)}x) answers {', '.join(spec.get('pairs') or [])}")
        for field in ("move", "when", "verification"):
            print(f"  {field + ':':<13} {' '.join(str(spec.get(field) or '').split())}")
    if not for_ and not name:
        print(f"{len(ledger)} moves answering {len({p for s in ledger.values() for p in (s or {}).get('pairs') or []})} "
              "failure shapes — `thea successes --for <file|task>` for the ones that apply")
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


def port_example_block() -> str:
    """The socket, drawn live: one file, one place and the tree, each as the glyph line `port` prints (3.46.0)."""
    import port  # noqa: PLC0415
    rows = [(t, port.line(port.record(t, None, "codebase", None, ROOT.resolve()), color=False)) for t in ("scripts/doctor.py", "scripts", ".")]
    return "```console\n" + "\n".join(f"$ thea port {t} --line\n{ln}" for t, ln in rows) + "\n```"


def glance_figures() -> dict:
    """The headline figures as data (3.54.0): docs/INDEX.md renders them and `.agent/facts.json` carries them."""
    from contextcost import footprint  # noqa: PLC0415
    a = atlas()
    return {"languages": len(route_targets()), "extensions": len(a.get("artifact_routes") or {}),
            "gates": len(a.get("gate_tools") or {}), "runtimes": len(a.get("runtime_entry") or []),
            "failures": len(a.get("agent_failure_modes") or {}), "successes": len(a.get("agent_success_patterns") or {}),
            "invariants": len(a.get("hard_invariants") or []), "instruments": len(a.get("instruments") or {}),
            "edges": _edges(), "deps": footprint()["dependencies"]}


def glance_block() -> str:
    """The headline figures, computed on every build: what a reader should know in one line (3.13.0)."""
    g = glance_figures()
    return (f"**{g['languages']}** languages · **{g['extensions']}** extensions · "
            f"**{g['gates']}** gates · **{g['runtimes']}** runtimes · "
            f"**{g['failures']}** failure shapes · **{g['successes']}** success moves · "
            f"**{g['invariants']}** invariants · **{g['instruments']}** instruments · "
            f"**{g['edges']}** agreement edges · **{g['deps']}** dependency")


def proof_flow_block() -> str:
    """The whole loop as one generated flowchart: plug in, guard, prove, learn. Every figure is computed.

    READS ON EITHER PAGE (3.54.0). A light outer card fixed black gaps between bands and became a white slab
    on a dark page. Now nothing is a page colour: bands are borders with no fill, nodes are mid-tint
    chips with dark text, lines and titles are mid-tones — each legible on white and on black alike.
    PHONE WIDTH: at most three nodes per row and two short lines per box. Measured: 506px wide scaled the
    text to ~10px in a 375px column; tight spacing and short labels give 390px, ~13px.
    No fontFamily (a font mermaid did not measure pushes text out of boxes), no labelled back-edge (it
    crossed the forward label and was clipped), no edge from a node into another band (mermaid then drops
    that band's direction). Commas, never semicolons, which end a mermaid statement.
    CLEAN OVER COMPLETE: two short lines per box, one shape per role (round = actor, cylinder = store,
    hexagon = verdict), labels only on verdict edges. NO RUNTIME NAMES: any agent, chat or model plugs in
    through the same doors.
    """
    a = atlas()
    packs, gates = len(route_targets()), len(a.get("gate_tools") or {})
    shapes = list((a.get("agent_failure_modes") or {}).values())
    moves, shells = len(a.get("agent_success_patterns") or {}), len((a.get("agent_policy") or {}).get("shell_shapes") or [])
    theme = ("    primaryColor: \"#e6f2e7\"\n    primaryBorderColor: \"#6f9f73\"\n    primaryTextColor: \"#14301a\"\n"
             "    lineColor: \"#7f9483\"\n    titleColor: \"#6f9f73\"\n    edgeLabelBackground: \"#e6f2e7\"\n"
             "    fontSize: \"15px\"\n")
    return ("```mermaid\n---\nconfig:\n  theme: base\n  themeVariables:\n" + theme +
            "  flowchart:\n    subGraphTitleMargin: {top: 4, bottom: 6}\n    padding: 4\n"
            "    nodeSpacing: 12\n    rankSpacing: 14\n"
            "---\nflowchart TB\n"
            "  accTitle: How Thea proves a change\n"
            "  accDescr: any agent, chat or model plugs in, each file routes to its gates, hooks guard, the same gates"
            " prove at commit, in CI and in thea verify, anything but PASS is refused, every verdict is kept\n"
            "  subgraph ask [1 · plug in]\n    direction LR\n"
            "    A([any agent<br>or chat]) --> I[CLI · MCP<br>hooks]"
            f" --> D[(atlas.yaml<br>{packs} languages)]\n  end\n"
            "  subgraph guard [2 · guard]\n    direction LR\n"
            f"    S([command]) --> W{{{{{shells}<br>shapes}}}}\n"
            "    W -->|match| Y[refused]\n    W -->|clear| O[runs]\n"
            f"    E([edit]) --> L[{gates} gates<br>+ lessons]\n  end\n"
            "  subgraph run [3 · prove]\n    direction LR\n"
            "    H([commit<br>PR · verify]) --> V{{exit<br>code}}\n"
            "    V -->|PASS| M[landed]\n    V -->|else| X[refused]\n  end\n"
            "  subgraph learn [4 · learn]\n    direction LR\n"
            f"    Q[(field<br>ledger)] --> F[{len(shapes)} shapes<br>{moves} moves]"
            " --> N[next port<br>+ judge]\n  end\n"
            "  ask --> guard --> run --> learn\n"
            "  classDef band fill:none,stroke:#6f9f73,stroke-dasharray:4 3\n  class ask,guard,run,learn band\n"
            "  classDef stop fill:#f6d5d2,stroke:#c0605a,color:#5c1410\n"
            "  classDef go fill:#cfe9d2,stroke:#4f9a58,color:#103d17\n"
            "  classDef store fill:#d6e4f5,stroke:#5f86b8,color:#0d2a4d\n"
            "  class X,Y stop\n  class M,O go\n  class D,Q,V,W store\n```")


def _edges() -> int:
    """How many declarations resolve to a file that implements them — the agreement graph's size.

    ON THE LANDING PAGE BECAUSE IT IS THE ONE FIGURE THAT SAYS WHETHER THE REST ARE BACKED. 42
    invariants and 63 instruments are claims; an edge is a claim with a file behind it. The number
    is GENERATED, and `agreement_errors` fails the build when any declaration resolves to none — so
    an edge count that stops rising beside a roster that keeps growing is visible rather than quiet.
    """
    from agreement import index  # noqa: PLC0415
    return sum(len(rows) for rows in index().values())


def settings_block() -> str:
    """What Thea does in each setting, rendered from first_sweep/settings: one declaration feeds CHAT.md
    and the landing page, so "who is this for" is answered by the contract and cannot drift from it."""
    rows = ["| where you use it | what Thea does there |", "|---|---|"]
    for setting, what in ((atlas().get("first_sweep") or {}).get("settings") or {}).items():
        rows.append(f"| {setting[0].upper() + setting[1:]} | {' '.join(str(what).split())} |")
    return "\n".join(rows)


# Named, not built from an f-string: a caller a text search can see (orphans.py found the indirection).
README_BLOCKS = {"gate-example": gate_example_block, "port-example": port_example_block, "proof-flow": proof_flow_block}
# NOT README: a wide table and a ten-figure line made the landing page read sideways (3.50.0).
ELSEWHERE_BLOCKS = {"settings": ("models/README.md", settings_block), "glance": ("docs/INDEX.md", glance_block)}


TIERS = {
    # MORE STRUCTURE FOR A SMALLER MODEL, LESS FOR A LARGER ONE (3.21.0): the same facts, different scaffolding.
    "small": ["work loop: run one command; exit 0 is a pass; otherwise read its LAST line, fix only that, re-run it",
              "scope: edit only the file named above; if another file seems needed, stop and say which and why",
              "do not stop until every command above exits 0 — a passing test with a failing gate is not done"],
    "mid": [],
    "frontier": [],
}


def steps(path_value: str, runtime: str, change: str, as_json: bool, tier: str = "mid") -> int:
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
    process = (a.get("processes") or {}).get("implementation") or {}
    plan += [f"stop when: {', '.join(process.get('stop_when') or [])} — escalate when: {', '.join(process.get('escalate_when') or [])}",
             f"accepted only with: {process.get('returns', 'every gate result, including those NOT RUN')}"]
    plan += (["autonomous? isolate it: python scripts/sandboxgen.py docker <contract>",
              "done only when: python scripts/verify.py exits 0",
              "return: python scripts/branchstate.py --land — a pull request, never a bare push"] if runs else
             ["return: the gate checklist above with each claim labelled; file any gap in Thea with the report verb"])
    plan += TIERS.get(tier, [])
    if tier == "frontier":
        plan = [s for s in plan if s.startswith(("prove with", "route", "return", "done only"))]
    if as_json:
        print(_json.dumps({"schema": 1, "command": "steps", "runtime": runtime, "tier": tier, "path": path_value, "route": route,
                           "change_class": change, "steps": plan}, indent=2))
    else:
        print("\n".join(f"{n}. {s}" for n, s in enumerate(plan, 1)))
    return 0 if route else 2


def role(name: str | None, as_json: bool) -> int:
    """`thea role [<name>]` — what an agent in this role may do, must not do, hands back, and when it ends."""
    import json as _json
    roles = atlas().get("agent_roles") or {}
    if name is None or name not in roles:
        print("\n".join(f"{r:<13} {' '.join(str((s or {}).get('hands_back')).split())}" for r, s in roles.items()))
        return 0 if name is None else 2
    spec = roles[name]
    if as_json:
        print(_json.dumps({"schema": 1, "command": "role", "role": name, **spec}, indent=2))
    else:
        print("\n".join(f"{k:>12}: {v}" for k, v in spec.items()))
    return 0


def resume(as_json: bool) -> int:
    """`thea resume` — where interrupted work stands and the one next action, rebuilt from state, never memory.

    A role switch, a killed session or a new agent picking up a lane all start here: the lane (ahead,
    behind, uncommitted), a plant a killed run left, the last audit event, and the last verify record."""
    import json as _json
    import subprocess

    from safeedit import _git_path, plant_leftovers  # noqa: PLC0415
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=600, check=False).stdout.strip()  # noqa: S603, S607
    branch = git("branch", "--show-current")
    counts = git("rev-list", "--left-right", "--count", "@{upstream}...HEAD").split() or ["?", "?"]
    dirty = len([ln for ln in git("status", "--porcelain").splitlines() if ln])
    last_verify = _git_path("thea-last-verify.json")
    verdict = _json.loads(last_verify.read_text(encoding="utf-8")) if last_verify.is_file() else None
    audits = sorted((ROOT / ".agent" / "audit").glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    last_event = (audits[-1].read_text(encoding="utf-8").splitlines() or [""])[-1] if audits else ""
    leftovers = plant_leftovers()
    from hostshape import JOURNAL, read_journal, unverified_steps  # noqa: PLC0415
    journal_entries, journal_findings = read_journal(_git_path(JOURNAL).parent)
    partial = unverified_steps(journal_entries)
    lessons_file = _git_path("thea-lessons.json")
    recurring = [k for k, n in (_json.loads(lessons_file.read_text(encoding="utf-8")) if lessons_file.is_file() else {}).items() if n >= 2]
    failed = [r["id"] for r in (verdict or {}).get("rows", []) if r["verdict"] not in ("PASS", "REUSED")]
    nxt = (f"repair the journal — {journal_findings[0]}" if journal_findings else
           "run `python scripts/atlas_test.py --restore` — a killed run left a plant" if leftovers else
           f"re-verify step {partial[-1]} — begun and never verified, so its write may be partial" if partial else
           f"fix {failed[0]}, then `thea verify`" if failed else
           "`thea verify` — nothing has proven this tree yet" if dirty and not verdict else
           "commit, then `python scripts/branchstate.py --land`" if dirty or counts[1] not in ("0", "?") else
           "start a task: `thea steps <file> --runtime <id>` under the role the user named")
    state = {"schema": 1, "command": "resume", "branch": branch, "behind": counts[0], "ahead": counts[1],
             "uncommitted": dirty, "plant_leftovers": len(leftovers), "unverified_steps": partial, "last_verify_exit": (verdict or {}).get("exit"),
             "failing_gates": failed, "recurring_failures": recurring[:3], "last_audit_event": _json.loads(last_event).get("event") if last_event else None,
             "next": nxt}
    print(_json.dumps(state, indent=2) if as_json else "\n".join(f"{k:>18}: {v}" for k, v in state.items() if k not in ("schema", "command")))
    return 1 if journal_findings else 0


# The knowledge commands, dispatched from one table so atlas.py stays under its cap as they grow.
COMMANDS = {
    "steps": lambda a: steps(a.path, a.runtime, a.change, a.json, a.tier),
    "failures": lambda a: draft(a.id or "", a.draft, a.json) if a.draft
        else __import__("agents").failures_shown(a.shown, a.route, atlas().get("agent_failure_modes") or {}) if a.shown
        else failures_matching(a.match, a.json) if a.match else failures(a.id, a.json, a.for_, a.limit),
    "successes": lambda a: successes(a.id, a.json, a.for_, a.limit),
    "role": lambda a: role(a.name, a.json),
    "judge": lambda a: __import__("judge").main([*([a.id] if a.id else []), *([a.answer] if a.answer else []), *([a.p] if a.p else []),
                                                  *[x for f in a.fact for x in ("--fact", f)],
                                                  *(["--calibrate", a.calibrate] if a.calibrate else []),
                                                  *(["--state", a.state] if a.state is not None else []),
                                                  *(["--to", a.to] if a.to else [])]),
    "model": lambda a: __import__("model").main([*(["--to", a.to] if a.to else []), *(["--json"] if a.json else [])]),
    "links": lambda a: __import__("links").main(["--json"] if a.json else []),
    "resume": lambda a: resume(a.json),
    "shell": lambda a: shell_hook(sys.stdin.read()) if a.hook else shell_check(" ".join(a.cmd), a.json),
    "brainstorm": lambda a: __import__("brainstorm").main([*(["--new"] if a.new else []), *a.record, *(["--json"] if a.json else [])]),
    "port": lambda a: port_hook(sys.stdin.read()) if a.hook else __import__("port").main([a.target, *(["--lens", a.lens] if a.lens else []), "--frame", a.frame,
                                               *(["--runtime", a.runtime] if a.runtime else []),
                                               *[f for f, on in (("--json", a.json), ("--line", a.line)) if on]]),
    "landed": lambda a: __import__("branchstate").landed(a.branch, a.base),
    "md": lambda a: __import__("mdshape").main([*([a.repo] if a.repo else []), *(["--staged"] if a.staged else []),
                                                *(["--base", a.base] if a.base else [])]),
    "delegate": lambda a: __import__("delegate").main(
        [*(["--task", a.task] if a.task else []), *(["--json"] if a.json else [])]),
    "handoff": lambda a: __import__("handoff").main(
        [a.path, *(["--task", a.task] if a.task else []), "--change", a.change, *(["--json"] if a.json else [])]),
    "cadence": lambda a: __import__("cadence").main(
        [*(["--minutes", str(a.minutes)] if a.minutes else []), *(["--json"] if a.json else [])]),
    "schedtargets": lambda a: __import__("schedtargets").main(
        [*(["--root", a.root] if a.root else []), *(["--platform", a.platform] if a.platform else [])]),
    "intake": lambda a: __import__("intake").main([*a.prompt, *(["--json"] if a.json else [])]),
}


def shell_check(command: str, as_json: bool) -> int:
    """`thea shell "<cmd>"` — the decider a runtime's own PreToolUse hook calls before running a command.

    WHY A COMMAND AND NOT ONLY A FUNCTION (3.27.0). Five standing verdicts in the ledger shared one reason:
    the shell belongs to the agent, so no FILE here can refuse it. A function fixes half of that and a
    COMMAND fixes the rest — every runtime can already run one, so the closer is the same in Claude Code,
    Codex, opencode or a bare shell, and it is plug-and-play: no import, no framework, one exit code.
    Exit 0 allows, 3 refuses. It FAILS OPEN on anything it cannot parse, because a guard that blocks
    correct commands gets switched off.
    """
    import json as _json

    from agentpolicy import shell_verdict  # noqa: PLC0415
    verdict = shell_verdict(command)
    _field_refusal(verdict, command)
    if as_json:
        print(_json.dumps({"schema": 1, "command": "shell", "allowed": verdict.allowed,
                           "control": verdict.control, "why": verdict.reason}, indent=2))
    else:
        print(("ALLOW  " if verdict.allowed else "REFUSE ") + verdict.reason)
    return 0 if verdict.allowed else 3


def _field_refusal(verdict, command: str) -> None:
    """A refusal onto the field ledger: the shape that fired and the command's digest, never its text.

    The shape id is what makes a refusal → resolution join possible: the same shape firing again in the
    same session is a re-fire; silence after it is the shape resolved.
    """
    if verdict.allowed:
        return
    import agentaudit  # noqa: PLC0415
    import agents  # noqa: PLC0415
    shape = agentaudit.digest(verdict.reason)["sha256"][:12]  # a shape's reason is fixed text: its hash is its id
    agents.field("field_refused", {"shape": shape, "command": agentaudit.digest(command)})


def hook_input(text: str) -> dict:
    """The `tool_input` of a runtime hook's stdin record (Claude Code and Codex share the shape), or {}.

    {} on anything unreadable: a hook that crashes on a record it did not expect gets switched off.
    """
    import json as _json

    try:
        record = _json.loads(text)
    except ValueError:
        return {}
    if isinstance(record, dict):
        _hook_beat(record)
    tool_input = record.get("tool_input") if isinstance(record, dict) else None
    return tool_input if isinstance(tool_input, dict) else {}


def _hook_beat(record: dict) -> None:
    """Every hook call is a heartbeat (3.54.0): the record carries `session_id` and `cwd`, so no second hook runs.

    FAILS OPEN and silent on a record with no session: a beat must never change a hook's answer.
    """
    import os  # noqa: PLC0415

    import agents  # noqa: PLC0415

    try:
        agents.beat(os.environ.get("THEA_AGENT") or "claude-code", record.get("session_id"), "hook", record.get("cwd"))
    except (agents.BeatError, OSError):
        return


def _hook_answer(event: str, **fields: str) -> None:
    import json as _json

    print(_json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}}))


def shell_hook(text: str) -> int:
    """`thea shell --hook`: a PreToolUse hook. A refused command is put to the person ("ask"), never denied.

    ADDS, NEVER SUBTRACTS (atlas.yaml/native_agent_tools): the person stays the decider, so the hook
    surfaces the verdict and leaves the tool in place. Exit 0 always; an allowed command prints nothing.
    """
    from agentpolicy import shell_verdict  # noqa: PLC0415
    command = hook_input(text).get("command")
    if not isinstance(command, str) or not command.strip():
        return 0
    verdict = shell_verdict(command)
    _field_refusal(verdict, command)
    if not verdict.allowed:
        _hook_answer("PreToolUse", permissionDecision="ask", permissionDecisionReason=f"thea shell: {verdict.reason}")
    return 0


def port_hook(text: str) -> int:
    """`thea port --hook`: a PostToolUse hook. The edited file's one-line plug reaches the agent as context."""
    import os  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import port  # noqa: PLC0415
    path = hook_input(text).get("file_path")
    if not isinstance(path, str) or not path:
        return 0
    try:  # the edited file's own repository is the tree, wherever the runtime started this process
        os.chdir(Path(path).expanduser().resolve().parent)
        rec = port.record(path, None, "agent", None)
    except (OSError, ValueError, KeyError):
        return 0
    if rec["route"] is not None:  # a file no pack routes has no gate to name: silence, not a "none" line
        _hook_answer("PostToolUse", additionalContext=rec["line"])
        shown = [lesson.get("failure") for lesson in rec.get("lessons") or [] if isinstance(lesson, dict)]
        if shown:
            import agents  # noqa: PLC0415
            agents.field("field_lesson", {"route": rec["route"], "failures": shown})
    return 0


if __name__ == "__main__":
    sys.exit(main())
