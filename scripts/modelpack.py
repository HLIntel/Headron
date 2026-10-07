"""modelpack — the student rung's loader: read a verified micro-pack bundle and answer from it. PURE STDLIB.

VENDORED, NOT WRITTEN HERE. Source: `student.py` and `bundle.py` of the private model repo at commit
3be2bcbb83993d827bd366c07490c4668dee1bee. Only the READ side is copied (features, the linear head, verify, active,
decide, status, the `thea model --json` record); training, bundling, attach and rollback stay in the private repo.
Renamed on the way in, nothing else: student.SCHEMA -> STUDENT_SCHEMA, bundle.SCHEMA -> MANIFEST_SCHEMA,
student.decide -> student_decide, and a message or docstring that named a private command or file is reworded.
A change here is a re-vendor from a named commit, never a hand edit:
model_test.py runs this file against scripts/fixtures/model/golden.json, which the source commit wrote, and fails
on any answer that moves by more than its tolerance.

What it refuses, each a NOT RUN and never a guess:
  * a bundle whose manifest or any pack fails its sha256 (checked on every read whose files changed);
  * a bundle or pack built for another judgments.yaml (sha256 of the text);
  * a missing link, manifest or pack, a pack of another schema, a file the manifest does not name.
A pack is a linear softmax head over hashed word 1-2-grams and char 3-grams, divided by a per-judgment temperature
fitted on a calibration split, so the p it returns is calibrated, not a raw score.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import re
import time
from pathlib import Path

STUDENT_SCHEMA = 2  # student.SCHEMA: one micro pack per judgment
MANIFEST_SCHEMA = 1  # bundle.SCHEMA
MODEL_SCHEMA = 1  # the `thea model --json` record the dashboard's Model page parses
MANIFEST = "manifest.json"
RUNGS = ("rules", "teacher", "student")
DASHBOARD = Path.home() / "Library" / "Application Support" / "Thea Dashboard" / "model"
REPO_DIR = Path(".thea") / "model"
BUCKETS = 1 << 18
_WORD = re.compile(r"[a-z0-9_]+")


class Stale(RuntimeError):
    """A pack that cannot be trusted (other schema, other judgments.yaml): NOT RUN, never a stale answer."""


class Refused(RuntimeError):
    """A bundle that must not be answered from; the message says why."""


# ---- student.py (read side) ----------------------------------------------------------------------------------------


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bucket(feature: str) -> int:
    return int.from_bytes(hashlib.blake2b(feature.encode("utf-8"), digest_size=4).digest(), "big") % BUCKETS


def features(text: str) -> dict[int, float]:
    """L2-normalised counts of hashed word 1-grams, word 2-grams and char 3-grams."""
    words = _WORD.findall(text.lower())
    feats: list[str] = [f"w:{w}" for w in words]
    feats += [f"b:{a} {b}" for a, b in itertools.pairwise(words)]
    for w in words:
        padded = f"<{w}>"
        feats += [f"c:{padded[i : i + 3]}" for i in range(len(padded) - 2)]
    counts: dict[int, float] = {}
    for f in feats:
        k = _bucket(f)
        counts[k] = counts.get(k, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def _softmax(z: list[float]) -> list[float]:
    top = max(z)
    ex = [math.exp(v - top) for v in z]
    s = sum(ex)
    return [v / s for v in ex]


def logits(head: dict, x: dict[int, float]) -> list[float]:
    z = list(head["b"])
    w = head["w"]
    for k, v in x.items():
        row = w.get(k)
        if row:
            for i, wi in enumerate(row):
                z[i] += wi * v
    return z


def predict(head: dict, x: dict[int, float]) -> list[float]:
    t = head.get("T", 1.0)
    return _softmax([v / t for v in logits(head, x)])


def load(path: Path) -> dict:
    pack = json.loads(Path(path).read_text(encoding="utf-8"))
    if pack.get("schema") != STUDENT_SCHEMA:
        raise Stale(f"pack schema {pack.get('schema')} is not {STUDENT_SCHEMA}")
    pack["head"]["w"] = {int(k): r for k, r in pack["head"]["w"].items()}
    return pack


def answer(pack: dict, x: dict[int, float], judgments_sha: str) -> dict:
    """{answer, p, dist} from one loaded pack, or {verdict: NOT RUN, why} when it was trained on another contract."""
    if pack.get("judgments_sha") != judgments_sha:
        return not_run(
            f"judgments.yaml sha {judgments_sha[:12]} is not the pack's {str(pack.get('judgments_sha'))[:12]}; rebuild"
        )
    head = pack["head"]
    dist = dict(zip(head["answers"], predict(head, x)))
    best = max(dist, key=dist.get)
    return {"answer": best, "p": round(dist[best], 4), "dist": dist}


def not_run(why: str) -> dict:
    return {"verdict": "NOT RUN", "why": why}


_CACHE: dict[Path, tuple[tuple[int, int], dict]] = {}


def _cached(path: Path) -> dict:
    """load(), re-read only when the file's mtime or size changed (a rebuilt pack is picked up without a restart)."""
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    hit = _CACHE.get(path)
    if not hit or hit[0] != key:
        hit = (key, load(path))
        _CACHE[path] = hit
    return hit[1]


def student_decide(pack_dir: Path, state: str, ids: list[str], judgments_text: str) -> dict:
    """{id: {answer, p, dist} | {verdict: NOT RUN, why}} from one feature pass over the state."""
    t0 = time.perf_counter()
    sha = sha256_text(judgments_text)
    x = features(state)
    out = {}
    for j in ids:
        path = Path(pack_dir) / f"{j}.json"
        try:
            out[j] = answer(_cached(path), x, sha)
        except FileNotFoundError:
            out[j] = not_run(f"no pack {path}")
        except (OSError, ValueError, KeyError, TypeError, Stale) as e:
            out[j] = not_run(f"pack {path} unreadable: {e}")
    out["_meta"] = {"backend": f"student:{Path(pack_dir).name}", "us": round((time.perf_counter() - t0) * 1e6, 1)}
    return out


# ---- bundle.py (read side) -----------------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(bundle_dir: Path) -> dict:
    """The manifest of bundle_dir when every pack in it is named, present, matches its sha256 and agrees with the
    manifest on schema, kind, judgment and judgments sha; Refused otherwise. Files the manifest does not name refuse
    too: a bundle carries only what it declares."""
    d = Path(bundle_dir)
    try:
        manifest = json.loads((d / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refused(f"REFUSED: no readable manifest in {d}: {e}") from e
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("student_schema") != STUDENT_SCHEMA:
        raise Refused(
            f"REFUSED: manifest schema {manifest.get('schema')}/{manifest.get('student_schema')} is not "
            f"{MANIFEST_SCHEMA}/{STUDENT_SCHEMA}"
        )
    if manifest.get("kind") != "base":
        raise Refused(f"REFUSED: a {manifest.get('kind')!r} bundle; only base packs ship")
    packs = manifest.get("packs") or {}
    if not packs:
        raise Refused(f"REFUSED: manifest in {d} names no pack")
    named = {p["file"] for p in packs.values()} | {MANIFEST}
    extra = sorted(f.name for f in d.iterdir() if f.name not in named)
    if extra:
        raise Refused(f"REFUSED: {d} holds files the manifest does not name: {extra}")
    for jid, p in packs.items():
        f = d / p["file"]
        if not f.is_file():
            raise Refused(f"REFUSED: {jid}: {p['file']} missing")
        got = sha256_file(f)
        if got != p["sha256"]:
            raise Refused(f"REFUSED: {jid}: sha256 {got[:12]} is not the manifest's {p['sha256'][:12]}")
        pack = json.loads(f.read_text(encoding="utf-8"))
        if pack.get("judgment") != jid or pack.get("judgments_sha") != manifest["judgments_sha"]:
            raise Refused(f"REFUSED: {jid}: pack disagrees with the manifest on judgment or judgments sha")
        if pack.get("kind") != "base":
            raise Refused(f"REFUSED: {jid}: a {pack.get('kind')!r} pack in a shipped bundle")
    return manifest


def _points_at(target: Path, name: str) -> str | None:
    link = target / name
    return os.readlink(link) if link.is_symlink() else None


_VERIFIED: dict[str, tuple[tuple, dict]] = {}


def active(target: Path) -> tuple[Path, dict]:
    """(bundle dir, manifest) of target/current, verified; re-verified whenever a file in it changed (mtime, size).
    The link is resolved once, so a swap during a read cannot mix two bundles."""
    link = Path(target) / "current"
    if not link.is_symlink():
        raise Refused(f"NOT RUN: no bundle attached at {target}; attach one from the private model repo")
    d = Path(os.path.realpath(link))
    try:
        stamp = tuple(sorted((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in d.iterdir()))
    except OSError as e:
        raise Refused(f"NOT RUN: {d} unreadable: {e}") from e
    hit = _VERIFIED.get(str(d))
    if not hit or hit[0] != stamp:
        hit = (stamp, verify(d))
        _VERIFIED[str(d)] = hit
    return d, hit[1]


def decide(target: Path, state: str, ids: list[str], judgments_text: str) -> dict:
    """student_decide over the active bundle of target: {id: {answer, p, dist} | {verdict: NOT RUN, why}}. Every
    judgment is NOT RUN when no bundle verifies or the bundle was built for another judgments.yaml."""
    try:
        d, manifest = active(target)
    except Refused as e:
        return {**{j: not_run(str(e)) for j in ids}, "_meta": {"backend": "bundle:none"}}
    sha = sha256_text(judgments_text)
    if manifest["judgments_sha"] != sha:
        why = f"bundle {d.name} built for judgments.yaml {manifest['judgments_sha'][:12]}, current is {sha[:12]}"
        return {**{j: not_run(why) for j in ids}, "_meta": {"backend": f"bundle:{d.name}"}}
    known = [j for j in ids if j in manifest["packs"]]
    out = student_decide(d, state, known, judgments_text) if known else {}
    for j in ids:
        if j not in manifest["packs"]:
            out[j] = not_run(f"bundle {d.name} has no pack for {j}")
    out["_meta"] = {**out.get("_meta", {}), "backend": f"bundle:{d.name}"}
    return out


def status(target: Path, judgments_text: str | None) -> dict:
    """{target, current, previous, judgments_sha, bundle_sha, built_at, stale, not_run: {id|_bundle: why}, manifest}.
    A missing judgments.yaml is a NOT RUN reason, never a pass."""
    target = Path(target)
    sha = sha256_text(judgments_text) if judgments_text is not None else None
    out = {
        "target": str(target),
        "current": _points_at(target, "current"),
        "previous": _points_at(target, "previous"),
        "judgments_sha": sha,
        "not_run": {},
        "manifest": None,
    }
    try:
        d, manifest = active(target)
    except Refused as e:
        out["not_run"]["_bundle"] = str(e)
        return out
    out.update(manifest=manifest, bundle_sha=manifest["judgments_sha"], built_at=manifest["built_at"])
    out["stale"] = sha is not None and manifest["judgments_sha"] != sha
    if sha is None:
        out["not_run"]["_bundle"] = "NOT RUN: no judgments.yaml read; staleness unknown"
    elif out["stale"]:
        out["not_run"]["_bundle"] = (
            f"NOT RUN: bundle built for judgments.yaml {manifest['judgments_sha'][:12]}, current is {sha[:12]}; "
            "attach a rebuilt bundle"
        )
    return out


def _heldout(entry: dict) -> dict | None:
    """The `thea model` heldout triple: of held-out OUTCOME rows the pack acted on (p >= bar), the share right. None
    when no outcome row was acted on: synthetic rows never stand in for an outcome score."""
    m = (entry.get("heldout") or {}).get("outcome") or {}
    if not m.get("acted") or m.get("right_acted") is None:
        return None
    return {"score": m["right_acted"], "rows": m["acted"], "bar": entry["bar"]}


def model_record(st: dict) -> dict:
    """The `thea model --json` record, schema 1: {schema, command, judgments_sha, judgments: {id: {rung, key,
    pack_sha, heldout}}}. pack_sha is the judgments sha the verified pack was trained on (the dashboard flags STALE
    when it differs); the table is empty when no bundle verifies. key names the env var the teacher needs, so it is
    null on the rules and student rungs."""
    manifest = st["manifest"] or {}
    table = {}
    for jid, e in sorted((manifest.get("packs") or {}).items()):
        rung = e["rung"] if e["rung"] in RUNGS else None
        table[jid] = {
            "rung": rung,
            "key": e["key"] if rung == "teacher" else None,
            "pack_sha": manifest["judgments_sha"],
            "heldout": _heldout(e),
        }
    return {"schema": MODEL_SCHEMA, "command": "model", "judgments_sha": st["judgments_sha"], "judgments": table}


def status_lines(st: dict) -> list[str]:
    lines = [f"target   {st['target']}", f"current  {st['current']}", f"previous {st['previous']}"]
    if st["manifest"]:
        m = st["manifest"]
        lines.append(
            f"bundle   built {m['built_at']} for judgments.yaml {m['judgments_sha'][:12]} "
            f"({len(m['packs'])} packs); current judgments.yaml {str(st['judgments_sha'])[:12]}"
            f"{' STALE' if st.get('stale') else ''}"
        )
        for jid, e in sorted(m["packs"].items()):
            h = _heldout(e)
            score = f"right_when_acted={h['score']} on {h['rows']} (bar {h['bar']})" if h else "no held-out outcome"
            lines.append(f"  {jid:<19} rung={e['rung']:<7} retires_key={e['key']} {score}")
    for k, why in sorted(st["not_run"].items()):
        lines.append(f"NOT RUN {k}: {why}")
    lines.append("STATUS " + ("NOT RUN" if st["not_run"] else "OK"))
    return lines
