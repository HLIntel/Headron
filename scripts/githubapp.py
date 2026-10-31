#!/usr/bin/env python3
"""The Headron GitHub App, one module: every pushed head gets a real "Headron verify" check run.

  python scripts/githubapp.py --base <sha> [--head HEAD] [--json]   # the verdict, locally
  python scripts/githubapp.py serve <port>                          # POST /github/webhook, GET /health
  python scripts/githubapp.py drain                                 # run every queued job once, then exit

ONE VERDICT FUNCTION. `build_report` runs `scripts/verify.py` (HEADRON_BASE = the PR base) in the tree it
grades; the service calls the same function over a checkout of each head, so a check run on GitHub and a
local run over the same SHAs cannot disagree. `conclusion` is the one verdict -> check-run mapping.

HARVESTED (3.56.0) from the App's first webhook, which ran outside this repository with the same wire
behaviour this keeps: POST /github/webhook, X-Hub-Signature-256, the env names below, check_suite /
check_run rerequested / pull_request events, the owner allowlist and the conclusion mapping. Added here:
a durable queue idempotent per (repo, head SHA), per-file annotations in batches of 50, and the
append-only refusal / override timeline.

SIGNATURE FIRST. A delivery is accepted only with `sha256=<hex>` equal to HMAC-SHA256 of the raw body
under the webhook secret, compared with `hmac.compare_digest` (constant-time). Unsigned, wrongly signed,
or secret-less deliveries are 401 before the body is parsed.

WHY AN OWNER ALLOWLIST. Verify runs the graded repository's own gates, so a head is code this host
executes. Only owners in HEADRON_APP_RUN_OWNERS (comma list; empty = none) are run, and the head's owner must
be listed too, so a fork's PR is never executed. Anything else gets a neutral NOT RUN that says why.

ENVIRONMENT ONLY, never printed: HEADRON_GITHUB_APP_ID, HEADRON_GITHUB_APP_PRIVATE_KEY_B64 (base64 PEM),
HEADRON_GITHUB_APP_WEBHOOK_SECRET, HEADRON_APP_RUN_OWNERS; optional HEADRON_GITHUB_APP_STATE (queue + timeline
directory, default $XDG_STATE_HOME/headron-github-app) and HEADRON_GITHUB_API (Enterprise Server).

WHY OPENSSL FOR RS256. The standard library has no RSA; `openssl dgst -sha256 -sign` makes the same
PKCS#1 v1.5 signature with no new wheel, and githubapp_test.py verifies the token with `openssl -verify`.

WHAT IT DOES NOT PROVE: that branch protection requires the check (`ghaudit.py` closes that).
githubapp_test.py proves the flow offline: recorded payloads, a fake GitHub transport, a real git checkout.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from atlascore import ROOT, atlas, diff_names, git_run
from runtime import resolve

CHECK_NAME = "Headron verify"
REPORT_HEADING = "## HEADRON REPORT"
WEBHOOK_PATH, HEALTH_PATH = "/github/webhook", "/health"
KEYS = ("HEADRON_GITHUB_APP_ID", "HEADRON_GITHUB_APP_PRIVATE_KEY_B64", "HEADRON_GITHUB_APP_WEBHOOK_SECRET")
API = "https://api.github.com"
MAX_BODY = 5 << 20  # GitHub caps a delivery at 25 MB; pull_request and check_suite payloads are far smaller
VERIFY_SECONDS = 1800
GIT_TIMEOUT = HTTP_TIMEOUT = SIGN_TIMEOUT = 60
INSTALL_TIMEOUT = 300
JWT_DRIFT, JWT_LIFETIME = 60, 540  # GitHub refuses an exp over 10 min out; iat back-dated for clock drift
ANNOTATION_BATCH = 50  # GitHub's per-request cap on annotations; later PATCHes append
TEXT_LIMIT = 65535  # GitHub's cap on output.summary / output.text
# A job whose worker died goes back to pending after the lease; a real run is bounded by VERIFY_SECONDS.
LEASE_SECONDS, MAX_ATTEMPTS = 2 * VERIFY_SECONDS, 3
REQUEST_TIMEOUT = 30  # a delivery that stops mid-body is dropped, not held on a thread forever
DRAIN_IDLE = 60  # the serve worker also wakes on every queued delivery
DONE_KEEP_SECONDS = 30 * 86400  # a done head older than this is forgotten (Queue.forget); a redelivery re-verifies
REFUSED = ("FAIL", "NOT RUN")
PR_ACTIONS = ("opened", "synchronize", "reopened")
STATES = ("pending", "running", "done")

Transport = Callable[[str, str, dict, "bytes | None"], tuple[int, dict]]


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return git_run(cwd or ROOT, *args)


def changed_files(base: str, head: str = "HEAD", tree: Path | None = None) -> list[str]:
    """Files the PR changes: base...head. An unresolvable base refuses rather than inventing []."""
    return diff_names(tree or ROOT, f"{base}...{head}")


def required_gates(files: list[str]) -> list[str]:
    """Gate ids the change class for these files would run — projection, not execution."""
    from agentpolicy import required_gates as _required  # noqa: PLC0415
    from branchstate import consumer_pin  # noqa: PLC0415

    change = (consumer_pin() or "source_change") if files else "source_change"
    return list(_required({"change_class": change, "risk_modifiers": []}))


def not_run(why: str) -> dict:
    """A verify record for a head that was not graded: neutral, with the reason as its one row."""
    row = {"id": "headron verify", "verdict": "NOT RUN", "why": why}
    return {"exit": 2, "stderr_tail": why, "verify": {"tally": {"NOT RUN": 1}, "rows": [row]}}


def run_verify(base: str | None, tree: Path | None = None) -> dict:
    """Headron verify in `tree` (verify grades the repository it runs in); --changed against base when known."""
    cwd = tree or ROOT
    if not (cwd / "atlas.yaml").is_file():
        return not_run("this head has no atlas.yaml; verify would grade the installed Headron, not this repository")
    # The head's gates run with this env, so the App's own keys never reach them: an allowlisted owner's
    # PR still runs its dependencies' code, and that code could read and post the private key.
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    # An atlas checkout (this repository, or a lane of it) is graded by its own verifier over its own tree.
    # A consumer carries atlas.yaml and NO scripts/verify.py, so the installed verifier grades it from cwd
    # (verify.target_tree); pointing HEADRON_ROOT at it would swap the installed policy for a missing one.
    own = cwd / "scripts" / "verify.py"
    if own.is_file():
        verifier, env["HEADRON_ROOT"] = own, str(cwd)
    else:
        verifier = ROOT / "scripts" / "verify.py"
    if base:
        env["HEADRON_BASE"] = base
    else:
        env.pop("HEADRON_BASE", None)
    argv = [sys.executable, str(verifier), "--json", *(["--changed"] if base else [])]
    try:
        done = subprocess.run(  # noqa: S603
            argv, cwd=cwd, capture_output=True, text=True, check=False, timeout=VERIFY_SECONDS, env=env
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return not_run(f"verify did not finish: {str(err)[:200]}")
    payload: dict = {}
    if done.stdout.strip():
        try:
            payload = json.loads(done.stdout)
        except json.JSONDecodeError:
            payload = {"raw": done.stdout[-2000:]}
    return {"exit": done.returncode, "stderr_tail": (done.stderr or "")[-1000:], "verify": payload}


def conclusion(exit_code: int | None, tally: Mapping) -> str:
    """Only complete, measured or reused evidence can pass; contradictory output cannot turn green."""
    if exit_code not in (0, 2, None):
        return "failure"
    if not isinstance(tally, Mapping) or any(
        key not in ("PASS", "REUSED", "FAIL", "NOT RUN") or type(value) is not int or value < 0
        for key, value in tally.items()
    ):
        return "neutral"
    if tally.get("FAIL", 0):
        return "failure"
    if exit_code == 0 and not tally.get("NOT RUN", 0) and tally.get("PASS", 0) + tally.get("REUSED", 0) > 0:
        return "success"
    return "neutral"


VERDICT = {"success": "PASS", "failure": "FAIL", "neutral": "NOT RUN"}


def merge_allowed(verdict: str) -> bool:
    """Anything but PASS refuses the merge — same rule as agent run, commit hook, and CI."""
    return verdict == "PASS"


def _gate_table(rows: list[dict]) -> str:
    lines = ["| gate | verdict | seconds | why |", "|---|---|---|---|"]
    for row in rows:
        why = str(row.get("why") or "").replace("|", "\\|").replace("\n", " ")[:300]
        lines.append(f"| `{row.get('id')}` | {row.get('verdict')} | {row.get('seconds', '')} | {why} |")
    return "\n".join(lines)


def check_run_payload(report: dict) -> dict:
    """GitHub check-run body: name, the conclusion, tally title, gate table + HEADRON REPORT."""
    verify = report.get("verify") or {}
    tally = verify.get("tally") or {}
    title = f"PASS {tally.get('PASS', 0)} · FAIL {tally.get('FAIL', 0)} · NOT RUN {tally.get('NOT RUN', 0)}"
    text = f"{_gate_table(verify.get('rows') or [])}\n\n{report['comment_markdown']}"
    return {
        "name": CHECK_NAME,
        "head_sha": report.get("head_sha"),
        "status": "completed",
        "conclusion": report["conclusion"],
        "output": {
            "title": title,
            "summary": f"`headron verify` exit {report.get('exit')} (contract {atlas().get('version')})",
            "text": text[:TEXT_LIMIT],
        },
    }


def comment_markdown(report: dict) -> str:
    """HEADRON REPORT body for the pull request (built; posting it as a comment is not wired)."""
    files = report.get("changed_files") or []
    gates = report.get("required_gates") or []
    blocked = "blocked" if not report["merge_allowed"] else "allowed"
    agent = report.get("agent") or {}
    lines = [
        REPORT_HEADING,
        "",
        f"**Verdict:** {report['verdict']}",
        f"**Merge:** {blocked}",
        f"**Agent:** `{agent.get('agent', 'unknown')}` (runtime `{agent.get('runtime', 'unknown')}`)",
        "",
        "### Changed files",
    ]
    lines += [f"- `{f}`" for f in files[:50]] or ["- _(none)_"]
    if len(files) > 50:
        lines.append(f"- … and {len(files) - 50} more")
    lines += ["", "### Required gates"]
    lines += [f"- `{g}`" for g in gates] or ["- _(none declared)_"]
    lines += ["", f"_Contract v{atlas().get('version')} · posted by the Headron GitHub App._"]
    return "\n".join(lines) + "\n"


def metrics_record(report: dict) -> dict:
    """Minimal metrics a future dashboard reads: counts, blocked, agent."""
    tally = (report.get("verify") or {}).get("tally") or {}
    passed = int(tally.get("PASS") or 0) + int(tally.get("REUSED") or 0)
    failed = int(tally.get("FAIL") or 0)
    not_run_count = int(tally.get("NOT RUN") or 0)
    return {
        "schema": 1,
        "kind": "headron_verification",
        "atlas_version": str(atlas().get("version")),
        "verifications": passed + failed + not_run_count,
        "pass": passed,
        "fail": failed,
        "not_run": not_run_count,
        "blocked": not report["merge_allowed"],
        "verdict": report["verdict"],
        "agent": (report.get("agent") or {}).get("agent"),
        "runtime": (report.get("agent") or {}).get("runtime"),
    }


def _assemble(base: str | None, head: str, head_sha: str, files: list[str], verify_result: dict) -> dict:
    verify = verify_result.get("verify") or {}
    concl = conclusion(verify_result.get("exit"), verify.get("tally") or {})
    report = {
        "base": base,
        "head": head,
        "head_sha": head_sha,
        "changed_files": files,
        "required_gates": required_gates(files),
        "exit": verify_result.get("exit"),
        "conclusion": concl,
        "verdict": VERDICT[concl],
        "merge_allowed": merge_allowed(VERDICT[concl]),
        "agent": resolve(),
        "verify": verify,
        "files_error": verify_result.get("files_error", ""),
    }
    report["comment_markdown"] = comment_markdown(report)
    report["check_run"] = check_run_payload(report)
    report["metrics"] = metrics_record(report)
    return report


def build_report(base: str | None, head: str = "HEAD", tree: Path | None = None, execute: bool = True) -> dict:
    """Assemble check-run, comment, and metrics from a base/head pair (base None = full verify, no diff)."""
    tree = tree or ROOT
    head_sha = _git("rev-parse", head, cwd=tree).stdout.strip() or head
    files, files_error = [], ""
    if base:
        try:
            files = changed_files(base, head, tree)
        except ValueError as err:
            files_error = str(err)
    verify_result = run_verify(base, tree) if execute else {"exit": 2, "verify": {}, "stderr_tail": "dry-run"}
    if files_error and execute:
        # An unresolvable base is incomplete, never a green merge.
        verify_result = {**verify_result, "exit": 2, "files_error": files_error}
    return _assemble(base, head, head_sha, files, verify_result)


def refused_report(head_sha: str, why: str) -> dict:
    """The report for a head this host will not execute: NOT RUN, neutral, the reason on the check run."""
    return _assemble(None, head_sha, head_sha, [], not_run(why))


class GitHubError(RuntimeError):
    """A non-2xx answer. The status travels as a field, so callers branch on it, never on the message."""

    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub answered {status}: {message}")
        self.status = status


# What a drain retries: GitHub, git and the host. Anything else is a bug and stops the worker loudly.
TRANSIENT = (GitHubError, RuntimeError, OSError, subprocess.TimeoutExpired)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def app_jwt(app_id: str, key_b64: str, now: float | None = None) -> str:
    """RS256 app JWT signed by openssl; the key touches disk only as a 0600 temp file, removed at once."""
    issued = int(now if now is not None else time.time())
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {"iat": issued - JWT_DRIFT, "exp": issued + JWT_LIFETIME, "iss": str(app_id)}
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    with tempfile.TemporaryDirectory(prefix="headron-app-key-") as scratch:
        pem = Path(scratch) / "app.pem"
        fd = os.open(pem, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(base64.b64decode(key_b64))
        done = subprocess.run(  # noqa: S603 - fixed argv, key is a path
            ["openssl", "dgst", "-sha256", "-sign", str(pem)],
            input=f"{header}.{payload}".encode(),
            capture_output=True,
            check=False,
            timeout=SIGN_TIMEOUT,
        )
    if done.returncode != 0 or not done.stdout:
        # openssl's stderr names the file and the parse error, never key material.
        raise RuntimeError(f"openssl could not sign the app JWT: {done.stderr.decode(errors='replace')[-300:]}")
    return f"{header}.{payload}.{_b64url(done.stdout)}"


def urllib_transport(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict]:
    """The one live transport: urllib, bounded, JSON in and out. Error bodies are returned, not raised."""
    # HEADRON_GITHUB_API is operator-set; a file: or custom scheme would let urlopen read local files.
    if not url.startswith("https://"):
        return 0, {"message": f"refused a non-https GitHub API URL: {url.split(':', 1)[0]}:"}
    request = urllib.request.Request(url, data=body, method=method, headers=headers)  # noqa: S310  # nosec B310
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as answer:  # noqa: S310  # nosec B310 - https checked above
            raw, status = answer.read(), answer.status
    except urllib.error.HTTPError as err:
        raw, status = err.read(), err.code
    except OSError as err:
        return 0, {"message": str(err)[:300]}
    try:
        return status, (json.loads(raw) if raw else {})
    except json.JSONDecodeError:
        return status, {"message": raw[:300].decode(errors="replace")}


def call(transport: Transport, bearer: str, method: str, path: str, body: dict | None = None) -> dict:
    """One API call; any non-2xx (or a network failure, status 0) raises GitHubError."""
    headers = {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "headron-github-app",
        "Content-Type": "application/json",
    }
    base = (os.environ.get("HEADRON_GITHUB_API") or API).rstrip("/")
    data = json.dumps(body).encode() if body is not None else None
    status, answer = transport(method, f"{base}{path}", headers, data)
    if not 200 <= status < 300:
        raise GitHubError(status, str((answer or {}).get("message") or "no message"))
    return answer


def env_tokens(transport: Transport) -> Callable[[int], str]:
    """Installation tokens from the env-configured App key — a fresh exchange each call, so a suite that
    outlives a token's hour still completes its check run."""

    def token_for(installation_id: int) -> str:
        app_id, key = (os.environ.get(k) or "" for k in KEYS[:2])
        if not (app_id and key):
            raise RuntimeError(f"{KEYS[0]} or {KEYS[1]} is not set")
        answer = call(
            transport, app_jwt(app_id, key), "POST", f"/app/installations/{int(installation_id)}/access_tokens"
        )
        if not answer.get("token"):
            raise GitHubError(201, "access_tokens answered without a token")
        return str(answer["token"])

    return token_for


def job_id(repo: str, sha: str) -> str:
    return hashlib.sha256(f"{repo}@{sha}".encode()).hexdigest()[:24]


def _write_atomic(path: Path, record: dict) -> None:
    scratch = path.with_suffix(".tmp")
    scratch.write_text(json.dumps(record, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    os.replace(scratch, path)


def _mtime(path: Path) -> float:
    """A listed record's age; one another worker moved since the listing sorts last instead of raising."""
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return float("inf")


def _append(path: Path, row: dict) -> None:
    """One line, O_APPEND, fsynced: a row is wholly present or absent after a crash. Nothing here truncates."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, (json.dumps(row, sort_keys=True) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def state_root() -> Path:
    explicit = os.environ.get("HEADRON_GITHUB_APP_STATE")
    xdg = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(explicit) if explicit else Path(xdg) / "headron-github-app"


class Queue:
    """One JSON file per job, moved pending/ -> running/ -> done/ by atomic rename, keyed by (repo, head SHA):
    a pull_request and its check_suite, or a redelivery, for the same bytes verify once. A crash leaves the
    job in exactly one directory; two workers racing for it, exactly one wins."""

    def __init__(self, root: Path):
        self.root = Path(root)
        for name in (*STATES, "keys"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def _path(self, state: str, jid: str) -> Path:
        return self.root / state / f"{jid}.json"

    def enqueue(self, job: dict) -> bool:
        """True when queued; False when (repo, head_sha) was already queued, running or done."""
        jid = job_id(job["repo"], job["head_sha"])
        try:
            os.close(os.open(self.root / "keys" / jid, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        except FileExistsError:
            return False
        _write_atomic(self._path("pending", jid), {**job, "id": jid, "attempts": 0, "queued_at": time.time()})
        return True

    def requeue(self, job: dict) -> bool:
        """A rerequest: verify a finished head again. False while it is still pending or running."""
        jid = job_id(job["repo"], job["head_sha"])
        if self._path("pending", jid).exists() or self._path("running", jid).exists():
            return False
        self._path("done", jid).unlink(missing_ok=True)
        (self.root / "keys" / jid).unlink(missing_ok=True)
        return self.enqueue(job)

    def claim(self) -> dict | None:
        """The newest ready pending job (higher priority for newer commits), moved to running; None when the queue is empty or deferred.

        WHY (3.60.0). Older commits for the same repo are likely superseded by newer pushes.
        Prioritizing newer commits means the worker grades the head that will actually merge,
        and can mark obsolete results when the source changes."""
        now = time.time()
        # Sort by mtime descending (newest first) to prioritize newer commits
        for path in sorted((self.root / "pending").glob("*.json"), key=_mtime, reverse=True):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                continue  # another worker claimed it between the listing and the read
            if float(record.get("not_before") or 0) > now:
                continue
            # Mark older jobs for the same repo as obsolete when a newer one is claimed
            repo = record.get("repo")
            if repo:
                self._mark_obsolete(repo, path)
            target = self.root / "running" / path.name
            try:
                os.rename(path, target)
            except FileNotFoundError:
                continue  # another worker won this one
            os.utime(target)  # the lease runs from the claim, not the enqueue
            return record
        return None

    def _mark_obsolete(self, repo: str, current_path: Path) -> None:
        """Mark older pending jobs for the same repo as obsolete — finalized NOT RUN, not re-graded."""
        current_sha = current_path.stem
        for path in (self.root / "pending").glob("*.json"):
            if path.name == current_path.name:
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            if record.get("repo") == repo:
                self.finalize_later(
                    record, f"superseded by newer commit {current_sha[:12]}", seconds=0, error="obsolete"
                )

    def complete(self, job: dict, result: dict) -> None:
        _write_atomic(self._path("done", job["id"]), {**job, "result": result, "done_at": time.time()})
        self._path("running", job["id"]).unlink(missing_ok=True)

    def defer(self, job: dict, why: str, seconds: float = 0) -> None:
        """Return a failed job to pending, optionally after a backoff, without losing its check-run id."""
        record = {**job, "attempts": int(job.get("attempts") or 0) + 1, "last_error": why}
        _write_atomic(self._path("pending", job["id"]), {**record, "not_before": time.time() + seconds})
        self._path("running", job["id"]).unlink(missing_ok=True)

    def finalize_later(self, job: dict, why: str, seconds: float = 0, error: str = "") -> None:
        """Pending, but only to complete its check run neutral: a drain never grades this head again."""
        self.defer({**job, "finalize": why}, error or why, seconds)

    def release(self, job: dict, why: str) -> bool:
        """Retry below the attempt cap; at the cap leave it claimed for terminal check-run finalization."""
        if int(job.get("attempts") or 0) + 1 >= MAX_ATTEMPTS:
            return False
        self.defer(job, why)
        return True

    def recover(self, lease: float = LEASE_SECONDS, now: float | None = None) -> int:
        """Running jobs whose lease expired go back to pending; returns how many.

        An expired lease is an attempt: a head that kills its worker (OOM, a hung gate past the lease) would
        otherwise be regraded every lease, forever. At the cap it comes back only to be completed neutral.
        """
        cutoff, moved = (now if now is not None else time.time()) - lease, 0
        for path in (self.root / "running").glob("*.json"):
            if _mtime(path) >= cutoff:
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                continue  # its worker finished between the listing and the read
            why = f"worker lease of {int(lease)}s expired"
            if int(record.get("attempts") or 0) + 1 >= MAX_ATTEMPTS:
                self.finalize_later(record, why)
            else:
                self.defer(record, why)
            moved += 1
        return moved

    def forget(self, keep: float = DONE_KEEP_SECONDS, now: float | None = None) -> int:
        """Done heads older than `keep` lose their record and dedupe key; returns how many.

        WHY (3.59.0): done/ and keys/ grew one entry per head ever graded and nothing removed them. A done
        record is derivable — its check run on GitHub is the record, and a refusal is in the timeline — so
        it is forgotten, not archived; a redelivery of a forgotten head verifies it again.
        """
        cutoff, gone = (now if now is not None else time.time()) - keep, 0
        for path in (self.root / "done").glob("*.json"):
            if _mtime(path) >= cutoff:
                continue
            path.unlink(missing_ok=True)
            (self.root / "keys" / path.stem).unlink(missing_ok=True)
            gone += 1
        return gone

    def result(self, repo: str, sha: str) -> dict | None:
        path = self._path("done", job_id(repo, sha))
        return json.loads(path.read_text(encoding="utf-8")).get("result") if path.is_file() else None

    def counts(self) -> dict:
        return {state: len(list((self.root / state).glob("*.json"))) for state in STATES}

    def record_installation(self, event: str, payload: dict) -> dict:
        """Who installed or removed the App, appended — the account list the service serves."""
        install = payload.get("installation") or {}
        added = (payload.get("repositories") or []) + (payload.get("repositories_added") or [])
        row = {
            "schema": 1,
            "at": time.time(),
            "event": event,
            "action": payload.get("action"),
            "installation_id": install.get("id"),
            "account": (install.get("account") or {}).get("login"),
            "repositories": [r.get("full_name") for r in added],
        }
        _append(self.root / "installations.jsonl", row)
        return row

    def timeline(self, row: dict) -> dict:
        """The audit record: one appended row per refusal (a head the App blocked) and per override."""
        record = {"schema": 1, "at": time.time(), **row}
        _append(self.root / "timeline.jsonl", record)
        return record

    def timeline_rows(self) -> list[dict]:
        path = self.root / "timeline.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def signed(secret: str, body: bytes, header: str | None) -> bool:
    """True only for `sha256=<hex>` matching HMAC-SHA256(secret, body); an empty secret signs nothing."""
    if not secret or not header or not header.startswith("sha256="):
        return False
    want = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, header[len("sha256=") :])


def allowed(owner: str, repo: str) -> bool:
    """Run only when the head's owner AND the repository's owner are allowlisted (a fork's PR fails the first)."""
    owners = {o.strip().lower() for o in os.environ.get("HEADRON_APP_RUN_OWNERS", "").split(",") if o.strip()}
    return owner.lower() in owners and repo.split("/")[0].lower() in owners


def job(event: str, payload: dict, delivery: str = "") -> dict | None:
    """The head to grade for an event that asks for a verdict; None for every other event."""
    action = payload.get("action")
    if event == "check_suite" and action in ("requested", "rerequested"):
        source = payload.get("check_suite") or {}
        sha, head_repo = source.get("head_sha"), source.get("head_repository") or {}
    elif (
        event == "check_run" and action == "rerequested" and (payload.get("check_run") or {}).get("name") == CHECK_NAME
    ):
        source = payload["check_run"]
        # The top-level repository is the installed/base repository. Trusting it as the head identity
        # lets a rerequested check on a fork inherit the allowlisted base owner.
        head_repo = (source.get("check_suite") or {}).get("head_repository") or {}
        sha = source.get("head_sha")
    elif event == "pull_request" and action in PR_ACTIONS:
        pr_head = (payload.get("pull_request") or {}).get("head") or {}
        source = {"pull_requests": [payload["pull_request"]]}
        sha, head_repo = pr_head.get("sha"), pr_head.get("repo") or {}
    else:
        return None
    repository = payload.get("repository") or {}
    repo, inst = repository.get("full_name"), (payload.get("installation") or {}).get("id")
    if not (repo and sha and inst):
        return None
    pr = next(iter(source.get("pull_requests") or []), None) or {}
    return {
        "repo": repo,
        "clone_url": repository.get("clone_url") or f"https://github.com/{repo}.git",
        "head_sha": sha,
        "base_sha": (pr.get("base") or {}).get("sha"),  # None for a push with no PR: a full verify, no diff
        "pr": pr.get("number"),
        "installation_id": int(inst),
        # Missing head identity fails closed in allowed(); never substitute the trusted base owner.
        "owner": ((head_repo.get("owner") or {}).get("login")) or "",
        "event": f"{event}.{action}",
        "delivery": delivery,
    }


def override_row(queue: Queue, payload: dict) -> dict | None:
    """A merged pull request whose head the App refused: the override the audit timeline exists to show."""
    pr = payload["pull_request"]
    repo, head = payload["repository"]["full_name"], pr["head"]["sha"]
    result = queue.result(repo, head)
    if result is None or result.get("verdict") == "PASS":
        return None  # merged before the App ever graded it: not provably an override
    return queue.timeline(
        {
            "kind": "override",
            "repo": repo,
            "pr": int(pr["number"]),
            "head_sha": head,
            "base_sha": pr["base"]["sha"],
            "verdict": result.get("verdict"),
            "blocked": result.get("blocked") or [],
            "actor": (pr.get("merged_by") or {}).get("login"),
            "merge_commit_sha": pr.get("merge_commit_sha"),
            "check_run_id": result.get("check_run_id"),
            "installation_id": int((payload.get("installation") or {}).get("id") or 0),
        }
    )


def handle(headers: Mapping[str, str], body: bytes, secret: str, queue: Queue) -> tuple[int, dict]:
    """(HTTP status, JSON body) for one delivery. Pure apart from the queue, so tests call it directly."""
    lower = {k.lower(): v for k, v in headers.items()}
    if not signed(secret, body, lower.get("x-hub-signature-256")):
        return 401, {"error": "bad signature"}
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return 400, {"error": "not JSON"}
    if not isinstance(payload, dict):
        return 400, {"error": "not a JSON object"}
    event, action = lower.get("x-github-event", ""), payload.get("action")
    if event == "ping":
        return 200, {"pong": True}
    if event in ("installation", "installation_repositories"):
        queue.record_installation(event, payload)
        return 200, {"recorded": event}
    if event == "pull_request" and action == "closed" and (payload.get("pull_request") or {}).get("merged"):
        return 200, {"override": override_row(queue, payload) is not None}
    work = job(event, payload, lower.get("x-github-delivery", ""))
    if work is None:
        return 204, {}
    queued = queue.requeue(work) if action == "rerequested" else queue.enqueue(work)
    return (202 if queued else 200), {"queued": queued}


def _git_auth(args: list[str], cwd: Path, token: str) -> subprocess.CompletedProcess:
    """git with the installation token as an http header passed through env — never argv, never .git/config."""
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraHeader"}
    env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False, timeout=GIT_TIMEOUT, env=env
    )


def checkout(work: dict, dest: Path, token: str) -> None:
    """Fetch a detached head, then prepare the exact tree the verifier is about to grade."""
    dest.mkdir(parents=True, exist_ok=True)
    shas = [work["head_sha"], *([work["base_sha"]] if work.get("base_sha") else [])]
    for args in (["init", "-q"], ["fetch", "-q", work["clone_url"], *shas], ["checkout", "-q", "--detach", shas[0]]):
        done = _git_auth(args, dest, token)
        if done.returncode:
            raise RuntimeError(f"git {args[0]} failed: {done.stderr.strip()[-300:]}")
    hooks = _git_auth(["config", "core.hooksPath", ".githooks"], dest, token)
    if hooks.returncode:
        raise RuntimeError(f"git config hooks failed: {hooks.stderr.strip()[-300:]}")
    lock = dest / "scripts" / "requirements.lock.txt"
    if lock.is_file():
        installed = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pip", "install", "--quiet", "--require-hashes", "-r", str(lock)],
            cwd=dest,
            capture_output=True,
            text=True,
            check=False,
            timeout=INSTALL_TIMEOUT,
        )
        if installed.returncode:
            raise RuntimeError(f"locked dependency install failed: {(installed.stderr or '').strip()[-300:]}")


def ledger_ids(why: str) -> list[str]:
    """Which declared failure shapes (atlas.yaml/agent_failure_modes) this gate's failure text is."""
    from knowledge import failure_ids  # noqa: PLC0415 - loads the atlas; only needed for a refusal

    return failure_ids(why) if why else []


def blocked_rows(report: dict) -> list[dict]:
    """Each gate that kept this head from merging: gate id (the guard), path, verdict, why, ledger ids."""
    rows = []
    for row in (report.get("verify") or {}).get("rows") or []:
        if row.get("verdict") not in REFUSED:
            continue
        gate, _, path = str(row.get("id") or "").partition(":")
        why = str(row.get("why") or "")
        rows.append(
            {"gate": gate, "path": path or None, "verdict": row["verdict"], "why": why, "ledger": ledger_ids(why)}
        )
    return rows


def file_annotations(report: dict, blocked: list[dict]) -> list[dict]:
    """One annotation per refused gate on a file this PR changed; whole-tree gates live in the summary."""
    changed = set(report.get("changed_files") or [])
    notes = []
    for row in blocked:
        if not row["path"] or row["path"] not in changed:
            continue
        did = "failed" if row["verdict"] == "FAIL" else "skipped"
        message = f"this change {did} its required gate `{row['gate']}`" + (f": {row['why']}" if row["why"] else "")
        notes.append(
            {
                "path": row["path"],
                "start_line": 1,
                "end_line": 1,
                "annotation_level": "failure" if row["verdict"] == "FAIL" else "warning",
                "title": f"{row['gate']}: {row['verdict']}",
                "message": message + (f" (ledger: {', '.join(row['ledger'])})" if row["ledger"] else ""),
            }
        )
    return notes


def annotation_batches(notes: list[dict]) -> list[list[dict]]:
    """At least one batch, so the completing PATCH always exists even with nothing to annotate."""
    return [notes[i : i + ANNOTATION_BATCH] for i in range(0, len(notes), ANNOTATION_BATCH)] or [[]]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def post_check_run(transport: Transport, token: str, work: dict, report: dict, notes: list[dict], run_id: int) -> None:
    """Annotate in batches of 50, completing on the last with the conclusion `conclusion` mapped."""
    payload = report["check_run"]
    batches = annotation_batches(notes)
    for index, batch in enumerate(batches):
        body: dict = {"output": {**payload["output"], "annotations": batch}}
        if index == len(batches) - 1:
            body |= {"status": "completed", "conclusion": payload["conclusion"], "completed_at": _now()}
        call(transport, token, "PATCH", f"/repos/{work['repo']}/check-runs/{run_id}", body)


def run_job(work: dict, queue: Queue, transport: Transport, token_for: Callable[[int], str]) -> dict:
    """Open the check run, grade the head, complete it; the result lands in done/ and, if refused, the timeline."""
    token = token_for(int(work["installation_id"]))
    run_id = work.get("check_run_id")
    if not run_id:
        started = call(
            transport,
            token,
            "POST",
            f"/repos/{work['repo']}/check-runs",
            {"name": CHECK_NAME, "head_sha": work["head_sha"], "status": "in_progress", "started_at": _now()},
        )
        run_id = work["check_run_id"] = int(started["id"])  # in place: a released retry reuses this run
    if allowed(work["owner"], work["repo"]):
        with tempfile.TemporaryDirectory(prefix="headron-app-head-") as scratch:
            tree = Path(scratch) / "tree"
            checkout(work, tree, token)
            report = build_report(work.get("base_sha"), work["head_sha"], tree=tree)
    else:
        why = f"owner {work['owner']} is not in this host's run allowlist (HEADRON_APP_RUN_OWNERS); its code is not executed here"
        report = refused_report(work["head_sha"], why)
    blocked = blocked_rows(report)
    notes = file_annotations(report, blocked)
    token = token_for(int(work["installation_id"]))  # a long suite can outlive the first token's hour
    post_check_run(transport, token, work, report, notes, run_id)
    result = {
        "verdict": report["verdict"],
        "conclusion": report["conclusion"],
        "merge_allowed": report["merge_allowed"],
        "check_run_id": run_id,
        "changed_files": report["changed_files"],
        "blocked": blocked,
        "annotations": len(notes),
        "metrics": report["metrics"],
    }
    queue.complete(work, result)
    if not report["merge_allowed"]:
        queue.timeline(refusal_row(work, report, blocked, run_id))
    return result


def refusal_row(work: dict, report: dict, blocked: list[dict], run_id: int | None) -> dict:
    """The timeline row for a head the App blocked — graded or given up on, one shape."""
    return {
        "kind": "refusal",
        "repo": work["repo"],
        "pr": work.get("pr"),
        "head_sha": work["head_sha"],
        "base_sha": work.get("base_sha"),
        "event": work.get("event"),
        "verdict": report["verdict"],
        "blocked": blocked,
        "check_run_id": run_id,
        "installation_id": work["installation_id"],
        "atlas_version": report["metrics"]["atlas_version"],
        "agent": report["metrics"]["agent"],
    }


def finish_give_up(work: dict, queue: Queue, transport: Transport, token_for: Callable[[int], str], why: str) -> dict:
    """Complete an exhausted check as neutral. It is never marked done before GitHub accepts the PATCH."""
    report = refused_report(work["head_sha"], f"gave up after {MAX_ATTEMPTS} attempts: {why}")
    run_id = work.get("check_run_id")
    if run_id:
        token = token_for(int(work["installation_id"]))
        post_check_run(transport, token, work, report, [], int(run_id))
    result = {
        "verdict": report["verdict"],
        "conclusion": report["conclusion"],
        "merge_allowed": False,
        "check_run_id": run_id,
        "changed_files": [],
        "blocked": blocked_rows(report),
        "annotations": 0,
        "metrics": report["metrics"],
        "why": report["verify"]["rows"][0]["why"],
    }
    queue.complete(work, result)
    queue.timeline(refusal_row(work, report, result["blocked"], run_id))
    return result


def drain(queue: Queue, transport: Transport, token_for: Callable[[int], str]) -> dict:
    """Run every pending job once; a job that hits GitHub or git trouble is released for a later drain."""
    queue.recover()
    queue.forget()
    tally = {"done": 0, "retried": 0, "gave_up": 0}
    while (work := queue.claim()) is not None:
        why = work.get("finalize")
        if not why:
            try:
                result = run_job(work, queue, transport, token_for)
                tally["done"] += 1
                print(f"{CHECK_NAME}: {result['conclusion']} {work['repo']}@{work['head_sha'][:7]}", flush=True)
                continue
            except TRANSIENT as err:
                why = str(err)[:300]
                if queue.release(work, why):
                    tally["retried"] += 1
                    continue
        try:
            finish_give_up(work, queue, transport, token_for, why)
            tally["gave_up"] += 1
        except TRANSIENT as final_err:
            # Do not forget an in-progress check. A later cycle retries ONLY the completion: the head was
            # already given up on, so grading it again would spend a full verify to reach the same refusal.
            queue.finalize_later(work, why, DRAIN_IDLE, f"terminal completion failed: {str(final_err)[:240]}")
            tally["retried"] += 1
    return tally


def make_handler(secret: str, queue: Queue, wake: threading.Event, keys_ok: bool) -> type[BaseHTTPRequestHandler]:
    class Hook(BaseHTTPRequestHandler):
        timeout = REQUEST_TIMEOUT

        def _send(self, code: int, obj: dict) -> None:
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802 - http.server's name
            if self.path == HEALTH_PATH:
                return self._send(200, {"ok": True, "keys": keys_ok, "queue": queue.counts()})
            return self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != WEBHOOK_PATH:
                return self._send(404, {"error": "not found"})
            raw = self.headers.get("Content-Length") or "0"
            size = int(raw) if raw.isdigit() else 0
            if size <= 0 or size > MAX_BODY:
                return self._send(413, {"error": "body size"})
            status, answer = handle(dict(self.headers.items()), self.rfile.read(size), secret, queue)
            if status == 202:
                wake.set()
            return self._send(status, answer)

        def log_message(self, format: str, *args: object) -> None:
            pass  # deliveries are logged by the worker, without headers

    return Hook


def serve(port: int) -> int:
    missing = [k for k in KEYS if not os.environ.get(k)]
    if missing:
        print(f"githubapp: NOT RUN — {', '.join(missing)} missing from the environment", file=sys.stderr)
        return 2
    queue, wake = Queue(state_root()), threading.Event()

    def worker() -> None:
        while True:
            try:
                drain(queue, urllib_transport, env_tokens(urllib_transport))
            except Exception as err:  # noqa: BLE001 — one bad drain must not stop the worker for every later job
                print(f"githubapp: drain error {type(err).__name__}: {str(err)[:200]}", flush=True)
            wake.wait(DRAIN_IDLE)
            wake.clear()

    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(os.environ[KEYS[2]], queue, wake, True))
    print(f"githubapp: listening on 127.0.0.1:{port}{WEBHOOK_PATH}, state {queue.root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["serve"]:
        if len(argv) != 2 or not argv[1].isdigit():
            print("usage: githubapp.py serve <port>  (no default: the host assigns it)", file=sys.stderr)
            return 2
        return serve(int(argv[1]))
    if argv[:1] == ["drain"]:
        queue = Queue(state_root())
        tally = drain(queue, urllib_transport, env_tokens(urllib_transport))
        print(json.dumps({**tally, "queue": queue.counts()}, sort_keys=True))
        return 0 if not tally["gave_up"] else 1
    parser = argparse.ArgumentParser(prog="githubapp.py", description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--base", required=True, help="PR base commit or ref (sets HEADRON_BASE for verify)")
    parser.add_argument("--head", default="HEAD", help="PR head commit or ref")
    parser.add_argument("--dry-run", action="store_true", help="shape only: skip running verify")
    parser.add_argument("--json", action="store_true", help="emit the full report record")
    parser.add_argument("--metrics-only", action="store_true", help="emit only the metrics record")
    args = parser.parse_args(argv)
    report = build_report(args.base, args.head, execute=not args.dry_run)
    if args.metrics_only:
        print(json.dumps(report["metrics"], indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["comment_markdown"], end="")
        print(f"check-run conclusion: {report['conclusion']}")
        print(f"metrics: {json.dumps(report['metrics'], sort_keys=True)}")
    return 0 if report["merge_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
