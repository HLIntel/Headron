#!/usr/bin/env python3
"""Where a fact may live, how it is retrieved, and the asymmetries underneath both.

Retrieval policy distinguishes knowledge that can live in weights from facts that must be retrieved or versioned.
The declarations are checked in both directions so retrieval and failure modes remain explicit.

WHAT THIS DOES NOT PROVE: that an index was BUILT this way. This checks the declaration is complete and self-consistent;
a retrieval system that ignores it is caught by the retrieval_change gate, and by a citation a reader can open.
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from atlascore import ROOT, atlas, route_targets, strict_yaml, text_of, tracked

if TYPE_CHECKING:
    pass


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

    A roster answers "what is supported" and never "what should I use", so a pack reachable only by already knowing its
    name is a pack nobody selects. An axis naming a pack that does not exist is a row in atlas.yaml/pointers.
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
    """docs/systems/<stem>.yaml — read from the resolved atlas, never shipped, like all policy content."""
    path = ROOT / "docs" / "systems" / f"{stem}.yaml"
    return (strict_yaml(text_of(path), str(path)) or {}) if path.is_file() else {}


def decision_records() -> dict:
    return system_records("decisions")


def decide(name: str | None, as_json: bool) -> int:
    """`atlas decide [<id>]` — the decision, when to choose each option, the failure, the proof."""
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
        _emit("decide", id=name, **spec, lessons=lessons_for(f"{spec.get('decides')} {spec.get('failure_mode')}"))
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
    import unicodedata  # noqa: PLC0415

    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    words = {w for w in _re.findall(r"[^\W_]+", normalized)
             if (len(w) > 2 or len(w) == 2 and not w.isascii()) and w not in _LESSON_STOP}
    # Unsegmented Han and Japanese text needs overlapping terms for partial lexical matches.
    for run in _re.findall(r"[\u3400-\u9fff\u3040-\u30ff]+", normalized):
        words.update(run[i:i + 2] for i in range(len(run) - 1))
    return words


LEDGERS = {
    "failures": ("agent_failure_modes", ("shape", "tell", "looks_like", "prevented_by"), "sightings"),
    "successes": ("agent_success_patterns", ("move", "when", "verification", "evidence"), "reused"),
}


def _flat(value: object) -> str:
    return " ".join(str(value or "").split())


def _emit(command: str, **fields: object) -> None:
    """The one JSON envelope both sides of the ledger print."""
    import json as _json  # noqa: PLC0415

    print(_json.dumps({"schema": 1, "command": command, "atlas_version": str(atlas().get("version")), **fields}, indent=2))


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
    return [{"failure": key, "tell": _flat((ledger.get(key) or {}).get("tell")),
             "do": next((_flat(m.get("move")) for _, m in moves_for(key)), None)}
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


def failure_ids(text: str) -> list[str]:
    """Declared shapes whose signature matches: one matcher for `failures --match` and the App's timeline."""
    import re as _re

    ledger = atlas().get("agent_failure_modes") or {}
    return [k for k, spec in ledger.items() if any(_re.search(p, text) for p in (spec or {}).get("signature") or [])]


def failures_matching(text: str, as_json: bool) -> int:
    """`headron failures --match TEXT` — which declared shapes an error text is, by atlas.yaml/agent_failure_modes signature.

    Reads the one declaration Headron Desktop and the model lab used to keep their own copy of."""
    ledger = atlas().get("agent_failure_modes") or {}
    hits = {key: ledger[key] for key in failure_ids(text)}
    if as_json:
        _emit("failures", match=True, failures=hits)
    elif not hits:
        print("no declared signature matches that text — `headron failures` lists the shapes; `--draft` files a new one")
    for key in hits if not as_json else ():
        print(f"{key} ({int(hits[key].get('sightings') or 0)}x)")
        print(f"  tell:    {_flat(hits[key].get('tell'))}")
        for sid, move in moves_for(key):
            print(f"  do:      {_flat(move.get('move'))} ({sid})")
    return 0 if hits else 1


def failures(name: str | None, as_json: bool, for_: str | None = None, limit: int = 3) -> int:
    """`headron failures [<id>]` — the ledger an agent learns from, without reading atlas.yaml (3.13.0).

    A reviewer called it the most original artifact here and found no way to see it but grepping YAML.
    Listing: every shape with its sightings and whether a program enforces it; an id prints the record."""
    ledger = atlas().get("agent_failure_modes") or {}
    if for_:
        picked = [(lesson["failure"], 0) for lesson in lessons_for(for_, limit)]
        if as_json:
            _emit("failures", **{"for": for_}, failures={k: ledger[k] for k, _ in picked},
                  moves={k: {s: m.get("move") for s, m in moves_for(k)} for k, _ in picked})
            return 0
        if not picked:
            print(f"none — no recorded shape shares a word with {for_!r}")
            return 0
        for key, _ in picked:
            spec = ledger[key] or {}
            print(f"{key} ({int(spec.get('sightings') or 0)}x)")
            print(f"  tell:    {_flat(spec.get('tell'))}\n  prevent: {_flat(spec.get('prevented_by'))}")
            for sid, move in moves_for(key):
                print(f"  do:      {_flat(move.get('move'))} ({sid})")
        return 0
    if as_json:
        _emit("failures", failures=ledger if name is None else {name: ledger.get(name)})
        return 0 if name is None or name in ledger else 2
    if name is None:
        for key, spec in sorted(ledger.items(), key=lambda kv: -int((kv[1] or {}).get("sightings") or 0)):
            spec = spec or {}
            guard = "guarded" if spec.get("enforced_by") else "standing verdict"
            answer = f" · do: {moves_for(key)[0][0]}" if moves_for(key) else ""
            print(f"{int(spec.get('sightings') or 0):>3}x  {key:<58} {guard}{answer}")
        guarded = sum(bool((spec or {}).get("enforced_by")) for spec in ledger.values())
        print(f"{len(ledger)} shapes: {guarded} guarded, {len(ledger) - guarded} standing verdict, most-sighted first — "
              "`headron failures <id>` for one, `headron successes` for the moves")
        return 0
    if name not in ledger:
        print(f"no failure mode '{name}' — `headron failures` lists them")
        return 2
    for field, value in (ledger[name] or {}).items():
        print(f"{field:>14}: {_flat(value)}")
    return 0


def draft(name: str, what: str, as_json: bool) -> int:
    """`headron failures <id> --draft "<what happened>"` — the ledger entry, prepared, never written (3.50.0).

    An agent that hits a mistake mid-task records it only when recording is one command. A known id gets
    its tell and the bump; a new id gets the nearest shapes (it may be one of them) and a `safeedit.py
    entry` line whose blank fields `check` refuses until filled — the id is the agent's, never invented."""
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
        _emit("failures", failures={name: known},
              draft={"id": name, "known": known is not None, "nearest": nearest, "command": command})
        return 0
    if known is not None:
        seen = int((known or {}).get("sightings") or 0)
        print(f"{name} is recorded ({seen}x): bump `sightings: {seen}` to {seen + 1} in atlas.yaml")
        print(f"  tell:    {_flat((known or {}).get('tell'))}")
        if seen + 1 >= 2 and not (known or {}).get("enforced_by"):
            print("  second sighting is a rule: name its guard in `enforced_by`, with a planted defect")
        return 0
    for key in nearest:
        print(f"nearest: {key} — `headron failures {key} --draft ...` if this is that shape again")
    print(command)
    print("fill every blank field; `headron check` refuses the entry until shape, tell, prevented_by and a closer are named")
    return 0


def successes(name: str | None, as_json: bool, for_: str | None = None, limit: int = 3) -> int:
    """`headron successes [<id>] [--for <file|task>]` — the moves that replaced recorded failures (3.43.0).

    A failure says what went wrong; its paired success says what to do instead, when, and how to prove it
    was done — the same fields an ATS task carries (move, when, verification). Each success names the
    failures it answers and the functions that prove it, so the two ledgers are one wired graph:
    failure -> move -> guard. JSON is the record an agent or another tool consumes."""
    ledger = atlas().get("agent_success_patterns") or {}
    keys = ([k for k, _ in relevant("successes", for_, limit)] if for_ else
            [name] if name else sorted(ledger, key=lambda k: -int((ledger[k] or {}).get("reused") or 0)))
    if name and name not in ledger:
        print(f"no success pattern '{name}' — `headron successes` lists them")
        return 2
    if as_json:
        _emit("successes", **({"for": for_} if for_ else {}), successes={k: ledger[k] for k in keys})
        return 0
    if for_ and not keys:
        print(f"none — no recorded move shares a word with {for_!r}")
    for key in keys:
        spec = ledger[key] or {}
        print(f"{key} ({int(spec.get('reused') or 0)}x) answers {', '.join(spec.get('pairs') or [])}")
        for field in ("move", "when", "verification"):
            print(f"  {field + ':':<13} {_flat(spec.get(field))}")
    if not for_ and not name:
        print(f"{len(ledger)} moves answering {len({p for s in ledger.values() for p in (s or {}).get('pairs') or []})} "
              "failure shapes — `headron successes --for <file|task>` for the ones that apply")
    return 0


def proof_flow_block() -> str:
    """The core protocol as a left-to-right flow, drawn as an SVG asset.

    The SVG draws its own navy card so its cyan/white text keeps contrast on light and dark pages.
    The asset is the drawing; this block places it.
    NO RUNTIME NAMES: any agent, chat or model reaches the core through the same doors.
    """
    return ('<p align="center">\n'
            '  <img src="docs/media/headron-proof-flow.svg" width="900"\n'
            '       alt="Headron routes, context, contracts, checks, receipts and an illustrative Harness view.">\n'
            '</p>')


def settings_block() -> str:
    """What Headron does in each setting, rendered from first_sweep/settings: one declaration feeds CHAT.md
    and the landing page, so "who is this for" is answered by the contract and cannot drift from it."""
    rows = ["| where you use it | what Headron does there |", "|---|---|"]
    for setting, what in ((atlas().get("first_sweep") or {}).get("settings") or {}).items():
        rows.append(f"| {setting[0].upper() + setting[1:]} | {' '.join(str(what).split())} |")
    return "\n".join(rows)


TIERS = {
    "small": ["work loop: run one command; exit 0 is a pass; otherwise read its LAST line, fix only that, re-run it",
              "scope: edit only the file named above; if another file seems needed, stop and say which and why",
              "do not stop until every command above exits 0 — a passing test with a failing gate is not done"],
    "mid": [],
    "frontier": [],
}


def role(name: str | None, as_json: bool) -> int:
    """`headron role [<name>]` — what an agent in this role may do, must not do, hands back, and when it ends."""
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


def _hook_answer(event: str, **fields: str) -> None:
    import json as _json

    print(_json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}}))


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    sys.exit(main())
