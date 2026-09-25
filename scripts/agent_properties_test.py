"""Property-based tests for the policy core: invariants over generated inputs, not planted examples.

WHY (2.28.0). agent_test plants the defects someone already imagined. A property states what must
hold for EVERY input — forbidden beats allowed, a lower budget never raises capacity, removing any
audit event breaks the chain — and a seeded generator hunts the boundary combinations no
hand-written fixture named. Stdlib `random` with a printed seed, so a failure replays exactly.

EACH PROPERTY IS MUTATION-TESTED BY CONSTRUCTION. It runs twice: against the real function, where
it must hold on every trial, and against a planted wrong implementation, where it must FAIL on at
least one. A property that also passes the mutant is too weak to catch the defect it names — the
harness is an instrument too. Counted into agent_test's CASES, so a skipped property moves its total.

WHAT IT DOES NOT PROVE. That the generator reaches every region: it draws from a declared alphabet
of path segments, budgets and fields. It widens what the planted suite covers; it does not replace it.
"""
from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path

import agentaudit
import agentpolicy
from agentpolicy import Verdict

SEED, TRIALS = 20260925, 200
SEGMENTS = ["a", "ab", "abc", "docs", "docsx", "lib", "src", "x1", "t_2", "z"]


def _path(rng: random.Random, depth: int = 3) -> str:
    return "/".join(rng.choice(SEGMENTS) for _ in range(rng.randint(1, depth)))


def forbidden_dominates(verdict) -> bool:
    rng = random.Random(SEED)
    for _ in range(TRIALS):
        forbidden = _path(rng, 2)
        child = f"{forbidden}/{_path(rng, 2)}" if rng.random() < 0.5 else forbidden
        contract = {"allowed_paths": [forbidden.split("/")[0]], "forbidden_paths": [forbidden]}
        if verdict(contract, child).allowed:
            return False
    return True


def prefix_is_a_boundary(prefixed) -> bool:
    rng = random.Random(SEED + 1)
    for _ in range(TRIALS):
        base = rng.choice(SEGMENTS)
        sibling = base + rng.choice(["x", "_old", "2"]) + "/" + _path(rng, 2)
        if prefixed(sibling, [base]) is not None:
            return False
    return True


def traversal_never_allowed(verdict) -> bool:
    rng = random.Random(SEED + 2)
    for _ in range(TRIALS):
        head = rng.choice(SEGMENTS)
        escape = rng.choice([f"{head}/../../{_path(rng)}", f"/{head}/{_path(rng)}", f"{head}/../../../etc"])
        if verdict({"allowed_paths": [head, "."], "forbidden_paths": []}, escape).allowed:
            return False
    return True


def budgets_monotone(effective) -> bool:
    rng = random.Random(SEED + 3)
    ceilings = agentpolicy.policy().get("default_budgets") or {}
    for _ in range(TRIALS):
        asked = {k: rng.randint(0, 2 * int(v)) for k, v in ceilings.items()}
        lower = {k: rng.randint(0, v) for k, v in asked.items()}
        high, low = effective({"budgets": asked}), effective({"budgets": lower})
        if any(high[k] > int(ceilings[k]) or low[k] > high[k] for k in ceilings):
            return False
    return True


def hash_is_identity(hasher) -> bool:
    rng = random.Random(SEED + 4)
    for _ in range(TRIALS):
        keys = rng.sample(["task_id", "objective", "allowed_paths", "base_commit", "budgets"], 4)
        contract = {k: rng.choice([1, "v", ["p"], {"n": rng.randint(0, 9)}]) for k in keys}
        shuffled = dict(reversed(list(contract.items())))
        changed = {**contract, keys[0]: ["changed", rng.random()]}
        if (hasher(contract) != hasher(shuffled) or hasher(contract) == hasher(changed)
                or hasher(contract) != hasher({**contract, "outcome": {"any": rng.random()}})):
            return False
    return True


def approval_binds_every_field(verdict) -> bool:
    rng = random.Random(SEED + 5)
    rules = agentpolicy.policy()["approval"]
    for _ in range(TRIALS):
        action = rng.choice(rules["required_for"])
        contract = {"base_commit": f"{rng.getrandbits(40):x}", "objective": rng.random()}
        diff, now = f"{rng.getrandbits(64):x}", rng.randint(10_000, 20_000)
        token = {"contract_hash": agentpolicy.contract_hash(contract), "action": action, "diff_hash": diff,
                 "repository": (agentpolicy.ROOT / "VERSION").parent.name, "base_commit": contract["base_commit"],
                 "issued_at": now - rng.randint(0, 60), "approver_role": rng.choice(rules["approver_roles"])}
        field = rng.choice(rules["binds_to"])
        if not verdict(contract, action, token, now, diff).allowed:
            return False
        if verdict(contract, action, {**token, field: "tampered"}, now, diff).allowed:
            return False
    return True


def audit_detects_any_loss(verify) -> bool:
    rng = random.Random(SEED + 6)
    kinds = agentaudit._rules()["events"]
    with tempfile.TemporaryDirectory() as tmp:
        for trial in range(TRIALS // 10):
            path = Path(tmp) / f"s{trial}.jsonl"
            for _ in range(rng.randint(3, 8)):
                agentaudit.append(path, rng.choice(kinds), {"n": rng.random()})
            lines = path.read_text(encoding="utf-8").splitlines()
            victim = rng.randrange(len(lines) - 1)
            if rng.random() < 0.5:
                del lines[victim]
            else:
                event = json.loads(lines[victim])
                event["body"] = {"n": "rewritten"}
                lines[victim] = json.dumps(event, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            if not verify(path):
                return False
    return True


def _allow_first(contract, candidate, mode="write"):
    if agentpolicy._prefixed(candidate, contract.get("allowed_paths")):
        return Verdict(True, "sandbox", "planted: allowed checked before forbidden")
    return agentpolicy.path_verdict(contract, candidate, mode)


PROPERTIES = [
    ("forbidden_paths dominates allowed_paths for every generated path", forbidden_dominates,
     agentpolicy.path_verdict, _allow_first),
    ("a prefix covers itself and its children, never a sibling sharing its spelling", prefix_is_a_boundary,
     agentpolicy._prefixed, lambda p, ps: next((x for x in ps if p.startswith(x)), None)),
    ("traversal and absolute paths are never allowed, even under an allow of '.'", traversal_never_allowed,
     agentpolicy.path_verdict,
     lambda c, p, m="write": Verdict(bool(agentpolicy._prefixed(p.lstrip("/"), c["allowed_paths"])), "sandbox", "")),
    ("a lower contract budget never raises capacity, and nothing exceeds the ceiling", budgets_monotone,
     agentpolicy.effective_budgets,
     lambda c: {k: max(int(v), int((c.get("budgets") or {}).get(k, v)))
                for k, v in (agentpolicy.policy().get("default_budgets") or {}).items()}),
    ("the contract hash ignores key order and outcome, and moves with any value", hash_is_identity,
     agentpolicy.contract_hash, lambda c: json.dumps(c, default=str)),
    ("an approval token refuses when ANY bound field is tampered", approval_binds_every_field,
     agentpolicy.approval_verdict,
     lambda c, a, t, now, d: agentpolicy.approval_verdict(c, a, {**t, "diff_hash": d}, now, d)),
    ("removing or rewriting any audit event breaks verification", audit_detects_any_loss,
     agentaudit.verify, lambda p: [x for x in agentaudit.verify(p) if "hash to its seal" in x]),
]


def run(harness) -> None:
    """Each property must HOLD on the real function and FAIL on its planted mutant."""
    for name, prop, real, mutant in PROPERTIES:
        held, killed = prop(real), not prop(mutant)
        harness.check(f"property: {name}", "an invariant that holds only on the examples someone wrote",
                      held and killed, f"real {'held' if held else 'BROKE'}, mutant {'killed' if killed else 'SURVIVED'}")
    print(f"  properties: {len(PROPERTIES)} x up to {TRIALS} trials, seed {SEED}, each mutation-tested")
