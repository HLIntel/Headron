#!/usr/bin/env python3
"""Shapes that break on the operator's HOST, checked from the records the host hands in.

WHY (3.47.0). Twelve shapes reached the ledger from one machine in one day — a session baseline nobody
measured, a worker killed mid-write, a snapshot that committed other writers' half-done edits, a self-update
that left a placeholder binary, a model changed and rebuilt with no eval, app state staged into a notes
repository, two daemons of one control plane, a tool rooted at its cwd instead of its configuration, and a
cache sweep that deleted the only copy of a build recipe. Each lives outside this tree, so none can be an
invariant here; each IS a pure function of a record the host can produce, so each is decided HERE, planted
in the suite, and run on the host by `python scripts/hostshape.py <check> ...` — the exit code is the verdict.

Every check refuses an ABSENT input rather than passing over it: a baseline nobody recorded, a sweep over a
path that is not there and a probe from one cwd are findings, never a clean pass.

WHAT IT DOES NOT PROVE. That the host runs it. A record handed in is only as honest as its producer, and a
check nobody schedules catches nothing — the ledger rows that name these functions say which host job must
call each one.
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from atlascore import atlas

JOURNAL = "thea-steps.jsonl"


def declared() -> dict:
    return atlas().get("host_shapes") or {}


def _matches(path: str, globs: list[str]) -> bool:
    """A glob matches the whole relative path or any tail of it, so a nested copy is not a way around it."""
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, f"*/{g}") for g in globs)


# --- A: a fixed context that grows unmeasured ---------------------------------------------------------

def baseline_errors(record: dict | None, now: float, max_age_hours: float) -> list[str]:
    """Each harness's first-turn cost is MEASURED, recent, under its budget, and the budget only falls."""
    harnesses = (record or {}).get("harnesses") or {}
    if not harnesses:
        return ["no harness baseline is recorded — a fixed context nobody measures grows until a session starts full"]
    errors: list[str] = []
    for name, row in sorted(harnesses.items()):
        budget, measured, at = row.get("budget_tokens"), row.get("measured_tokens"), row.get("measured_at")
        if not isinstance(budget, int) or not isinstance(measured, int) or not isinstance(at, (int, float)):
            errors.append(f"{name}: budget_tokens, measured_tokens and measured_at are all required — "
                          "an unmeasured harness is not an under-budget one")
            continue
        if measured > budget:
            errors.append(f"{name}: first turn measured {measured} tokens against a budget of {budget}")
        if now - at > max_age_hours * 3600:
            errors.append(f"{name}: the baseline instrument last ran {round((now - at) / 3600, 1)}h ago "
                          f"(bound {max_age_hours}h) — a stale reading is not a measurement")
        prior = [int(b) for b in row.get("budget_history") or [] if isinstance(b, int)]
        if prior and budget > min(prior) and not str(row.get("raised_for") or "").strip():
            errors.append(f"{name}: budget rose to {budget} from {min(prior)} with no raised_for — the "
                          "ratchet only falls")
    return errors


# --- B: a worker's steps, journaled so a kill is visible and a snapshot can wait --------------------

def unverified_steps(entries: list[dict]) -> list[str]:
    """`worker:step` for every step begun and not yet verified, in the order they were begun."""
    open_steps: dict[str, None] = {}
    for entry in entries:
        key = f"{entry.get('worker') or '-'}:{entry.get('step')}"
        if entry.get("state") == "begin":
            open_steps[key] = None
        elif entry.get("state") == "verified":
            open_steps.pop(key, None)
    return list(open_steps)


def resume_errors(entries: list[dict]) -> list[str]:
    """A step begun and never verified is a partial write until something re-verifies it."""
    return [f"step {key} was begun and never verified — a killed worker leaves exactly this; re-verify it "
            "before any later step or any claim of done" for key in unverified_steps(entries)]


def snapshot_errors(entries: list[dict], index_locked: bool) -> list[str]:
    """A snapshot of a shared checkout waits while any writer is mid-step or git itself holds the index."""
    errors = [f"step {key} is in flight — a snapshot now commits another writer's unverified edit"
              for key in unverified_steps(entries)]
    return errors + (["the index is locked — a writer is mid-commit"] if index_locked else [])


def read_journal(git_dir: Path) -> tuple[list[dict], list[str]]:
    """Entries plus findings: an unreadable journal line is a finding, never a crash or a silent skip."""
    path = git_dir / JOURNAL
    if not path.is_file():
        return [], []  # no worker has journaled a step: nothing is in flight, which is a state, not a skip
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return [], [f"journal: cannot read {path.name} — {error}"]
    entries, findings = [], []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            findings.append(f"journal line {line_number}: malformed JSON — {error.msg}")
            continue
        if isinstance(entry, dict):
            entries.append(entry)
        else:
            findings.append(f"journal line {line_number}: expected a JSON object")
    return entries, findings


def journal_resume_errors(git_dir: Path) -> list[str]:
    entries, malformed = read_journal(git_dir)
    return malformed + resume_errors(entries)


def journal_snapshot_errors(git_dir: Path, index_locked: bool) -> list[str]:
    entries, malformed = read_journal(git_dir)
    return malformed + snapshot_errors(entries, index_locked)


# --- C: a change to a toolchain or a model is followed by a CAPABILITY probe --------------------------

def change_probe_errors(events: list[dict]) -> list[str]:
    """Every change is followed by a passing capability probe of the same subject — presence is not capability."""
    errors: list[str] = []
    for change in (e for e in events if e.get("kind") == "change"):
        later = [e for e in events if e.get("kind") == "probe" and e.get("subject") == change.get("subject")
                 and float(e.get("at") or 0) >= float(change.get("at") or 0)]
        if any(p.get("probe") == "capability" and p.get("passed") is True for p in later):
            continue
        weaker = sorted({str(p.get("probe")) for p in later if p.get("probe") != "capability"})
        errors.append(f"{change.get('subject')}: changed ({change.get('what') or 'unstated'}) with no passing "
                      "capability probe after it" + (f" — only {', '.join(weaker)}, which a placeholder or a "
                                                     "broken template also passes" if weaker else ""))
    return errors


def chat_template_errors(template: str | None) -> list[str]:
    """A chat template that renders the bare prompt drops the roles the model was trained on."""
    body = "".join((template or "").split())
    if not body:
        return ["the rebuilt model carries no chat template — rebuild from the live model's own recipe"]
    if body.replace("{{.Prompt}}", "").replace("{{.Input}}", "") == "":
        return ["the chat template renders only the raw prompt — no system, role or turn markers survive, so the "
                "model answers a completion, not an instruction"]
    return []


def binary_errors(path: Path, min_bytes: int) -> list[str]:
    """After an update the binary is there, executable, and not a stub smaller than any real build."""
    if not path.exists():
        return [f"{path.name}: not there after the update — the link or the binary was removed"]
    if not os.access(path, os.X_OK):
        return [f"{path.name}: present and not executable"]
    head = path.read_bytes()[:2]
    size = path.stat().st_size
    if head != b"#!" and size < min_bytes:
        return [f"{path.name}: {size} bytes against a floor of {min_bytes} — a placeholder, not a build"]
    return []


# --- D: data a repository or a sweep must never touch ------------------------------------------------

def app_state_errors(paths: list[str], globs: list[str]) -> list[str]:
    """Tracked or staged paths that are an application's own state, not the notes it edits."""
    return [f"{p}: application state — ignore it by declaration, never commit it" for p in paths if _matches(p, globs)]


def sweep_errors(candidates: list[Path], markers: list[str], derivable: list[str], limit: int) -> list[str]:
    """A cleanup deletes only what can be re-derived: a source-shaped file outside a derivable dir is refused."""
    errors: list[str] = []
    walked = 0
    for root in candidates:
        if not root.exists():
            errors.append(f"{root}: not there — a sweep plan naming a missing path was built from a stale listing")
            continue
        for path in ([root] if root.is_file() else root.rglob("*")):
            walked += 1
            if walked > limit:
                return [*errors, f"walked {limit} entries without finishing — REFUSING the sweep rather than "
                        "guessing that the rest is derivable"]
            parts = set(path.parts)
            if path.is_file() and _matches(path.name, markers) and not parts & set(derivable):
                errors.append(f"{path}: a source-shaped file under a sweep — not re-derivable unless its "
                              "directory is declared derivable")
    return errors


# --- E: probes that depend on where, and daemons that must be one ------------------------------------

def singleton_errors(processes: list[dict], singletons: dict[str, str]) -> list[str]:
    """At most one running instance per declared singleton, matched on its command line."""
    errors: list[str] = []
    for name, needle in sorted(singletons.items()):
        pids = [str(p.get("pid")) for p in processes if needle in str(p.get("command") or "")]
        if len(pids) > 1:
            errors.append(f"{name}: {len(pids)} instances (pids {', '.join(pids)}) — two claimants of one queue")
    return errors


def root_drift_errors(configured: list[str], effective_by_cwd: dict[str, list[str]]) -> list[str]:
    """A tool's effective roots equal its configured roots from every cwd, including one outside them all."""
    if len(effective_by_cwd) < 2:
        return ["probed from fewer than two working directories — a cwd-rooted tool passes from the right one"]
    if all(any(cwd.startswith(root) for root in configured) for cwd in effective_by_cwd):
        return ["no probe ran from a cwd outside every configured root — the neutral cwd is the one that fails"]
    return [f"from {cwd}: effective roots {sorted(roots)} differ from configured {sorted(configured)}"
            for cwd, roots in sorted(effective_by_cwd.items()) if sorted(roots) != sorted(configured)]


# --- the host's entry points -------------------------------------------------------------------------

def _git_dir() -> Path:
    where = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True,  # noqa: S607
                           check=False, timeout=60).stdout.strip()
    if not where:
        raise SystemExit("not inside a git repository — the journal lives in the repository's git dir")
    return Path(where).resolve()


def _json_arg(argv: list[str]) -> object:
    if not argv:
        print("hostshape: JSON input path is required", file=sys.stderr)
        raise SystemExit(2)
    path = Path(argv[0])
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"hostshape: cannot read JSON input {path} — {error}", file=sys.stderr)
    except (UnicodeError, json.JSONDecodeError) as error:
        print(f"hostshape: cannot parse JSON input {path} — {error}", file=sys.stderr)
    raise SystemExit(2)


def _tracked_and_staged() -> list[str]:
    out = subprocess.run(["git", "ls-files", "--cached"], capture_output=True, text=True,  # noqa: S607
                         check=False, timeout=60).stdout
    return [line for line in out.splitlines() if line]


def _processes() -> list[dict]:
    out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True,  # noqa: S607
                         check=False, timeout=60).stdout
    return [{"pid": ln.split(None, 1)[0], "command": ln.split(None, 1)[-1]} for ln in out.splitlines() if ln.strip()]


def _step(argv: list[str]) -> list[str]:
    state, step = argv[0], argv[1]
    if state not in ("begin", "verified"):
        raise SystemExit("step takes begin|verified <name>")
    with (_git_dir() / JOURNAL).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"worker": os.environ.get("THEA_WORKER") or str(os.getppid()), "step": step,
                                 "state": state, "at": time.time()}) + "\n")
    return []


CHECKS = {
    "baseline": lambda a: baseline_errors(_json_arg(a), time.time(), float(declared().get("baseline_max_age_hours") or 26)),
    "resume": lambda a: journal_resume_errors(_git_dir()),
    "snapshot": lambda a: journal_snapshot_errors(_git_dir(), (_git_dir() / "index.lock").exists()),
    "step": _step,
    "changes": lambda a: change_probe_errors(list(_json_arg(a) or [])),
    "template": lambda a: chat_template_errors(Path(a[0]).read_text(encoding="utf-8") if a else None),
    "binary": lambda a: binary_errors(Path(a[0]), int(declared().get("min_binary_bytes") or 16384)),
    "app-state": lambda a: app_state_errors(_tracked_and_staged(), list(declared().get("app_state_globs") or [])),
    "sweep": lambda a: sweep_errors([Path(p) for p in a], list(declared().get("source_markers") or []),
                                    list(declared().get("derivable_dirs") or []), int(declared().get("sweep_walk_limit") or 50000)),
    "singletons": lambda a: singleton_errors(_processes(), dict(_json_arg(a) or {})),
    "roots": lambda a: root_drift_errors(*(lambda r: (r.get("configured") or [], r.get("effective_by_cwd") or {}))(_json_arg(a) or {})),
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in CHECKS:
        print(f"usage: hostshape.py {{{'|'.join(CHECKS)}}} [input] — the exit code is the verdict")
        return 2
    errors = CHECKS[argv[0]](argv[1:])
    for error in errors:
        print(f"- {error}")
    print(f"hostshape {argv[0]}: {len(errors)} finding(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
