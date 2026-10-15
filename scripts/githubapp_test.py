#!/usr/bin/env python3
"""Planted cases for the GitHub App (3.56.0): signature, events, JWT, queue, check run, timeline — offline.

Every case runs against recorded webhook payloads (scripts/fixtures/github) and a FAKE transport that
records each API call; nothing here reaches the network. The two decisions a defect would turn silently
permissive — the webhook signature check and the verdict -> conclusion mapping — are each planted wrong in
the source and the case must see it, because a check that cannot fail is decoration.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

ROOT = CASES = cast(Any, None)
SECRET = "fixture-webhook-secret"
FIXTURES = "scripts/fixtures/github"
WANT_CASES = 11
TIMEOUT = 60


def run(module) -> None:
    global ROOT, CASES
    ROOT, CASES = module.ROOT, module.CASES
    before = len(CASES)
    with tempfile.TemporaryDirectory(prefix="thea-app-test-") as scratch:
        work = Path(scratch)
        signature_cases(module)
        conclusion_cases(module)
        event_case()
        run_verify_tree_case(work)
        jwt_case(work)
        queue_case(work)
        batch_case()
        finish_give_up_case(work)
        end_to_end_case(work)
    if len(CASES) - before != WANT_CASES:
        raise SystemExit(f"githubapp_test registered {len(CASES) - before} cases, want {WANT_CASES}")
    print("  ok    githubapp flow cases")


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _signature_defects() -> list[str]:
    """Each way a forged or unsigned delivery could pass; empty = the check refuses all of them."""
    import githubapp

    body = b'{"action":"opened"}'
    wrong = []
    if not githubapp.signed(SECRET, body, _sign(body)):
        wrong.append("a correctly signed body was refused")
    key = SECRET.encode()
    forged = {
        "wrong secret": _sign(body, "other-secret"),
        "tampered body": _sign(body + b" "),
        "no header": None,
        "sha1 prefix": "sha1=" + hmac.new(key, body, hashlib.sha1).hexdigest(),
        "bare hex": hmac.new(key, body, hashlib.sha256).hexdigest(),
    }
    wrong += [f"{name} accepted" for name, header in forged.items() if githubapp.signed(SECRET, body, header)]
    if githubapp.signed("", body, _sign(body, "")):
        wrong.append("an unset secret accepted a body signed with the empty key")
    return wrong


def signature_cases(module) -> None:
    import githubapp

    if defects := _signature_defects():
        raise SystemExit(f"FAIL webhook signature: {defects}")
    CASES.append(("webhook signature accepts only HMAC-SHA256 under the secret", "anyone on the network queues runs"))
    planted = 'return hmac.compare_digest(want, header[len("sha256=") :])'
    with module.mutated("scripts/githubapp.py", lambda s: s.replace(planted, "return True")):
        importlib.reload(githubapp)
        caught = _signature_defects()
    importlib.reload(githubapp)
    if not caught:
        raise SystemExit("FAIL a signature check that accepts everything passed the signature case")
    CASES.append(("MUTATION: a signature check that always accepts is caught", "a decorative signature case"))


def _conclusion_defects() -> list[str]:
    """The harvested mapping: green only for exit 0 that measured something; FAIL or a crash is red."""
    import githubapp

    want = [
        ((0, {"PASS": 3}), "success"),
        ((0, {}), "neutral"),  # exit 0 that measured nothing is never green
        ((1, {"PASS": 2, "FAIL": 1}), "failure"),
        ((2, {"PASS": 2, "NOT RUN": 1}), "neutral"),
        ((2, {"FAIL": 1}), "failure"),
        ((None, {}), "neutral"),
        ((137, {"PASS": 5}), "failure"),  # killed mid-run
    ]
    wrong = [f"{args} -> {got}, want {c}" for args, c in want if (got := githubapp.conclusion(*args)) != c]
    for verdict, ok in (("PASS", True), ("FAIL", False), ("NOT RUN", False)):
        if githubapp.merge_allowed(verdict) is not ok:
            wrong.append(f"merge_allowed({verdict}) is not {ok}")
    if githubapp.VERDICT != {"success": "PASS", "failure": "FAIL", "neutral": "NOT RUN"}:
        wrong.append(f"conclusion -> verdict drifted: {githubapp.VERDICT}")
    return wrong


def conclusion_cases(module) -> None:
    import githubapp

    if defects := _conclusion_defects():
        raise SystemExit(f"FAIL conclusion mapping: {defects}")
    CASES.append(
        ("success needs exit 0 AND a PASS; FAIL or a crash is failure; else neutral", "a red verify posts green")
    )
    with module.mutated("scripts/githubapp.py", lambda s: s.replace('return "failure"', 'return "success"', 1)):
        importlib.reload(githubapp)
        caught = _conclusion_defects()
    importlib.reload(githubapp)
    if not caught:
        raise SystemExit("FAIL a FAIL -> success mapping passed the conclusion case")
    CASES.append(("MUTATION: FAIL mapped to success is caught", "a decorative conclusion case"))


def event_case() -> None:
    """Which deliveries ask for a verdict, and whose code the host will execute."""
    import githubapp

    repo = {"full_name": "example-org/r", "clone_url": "https://example.invalid/r.git"}
    pr = {"number": 3, "base": {"sha": "b" * 40}}
    suite = {"head_sha": "a" * 40, "pull_requests": [pr], "head_repository": {"owner": {"login": "example-org"}}}
    common = {"repository": repo, "installation": {"id": 9}}
    got = githubapp.job("check_suite", {**common, "action": "requested", "check_suite": suite}) or {}
    if (got.get("head_sha"), got.get("base_sha"), got.get("pr"), got.get("owner")) != (
        "a" * 40,
        "b" * 40,
        3,
        "example-org",
    ):
        raise SystemExit(f"FAIL check_suite job {got}")
    rerun = {
        **common,
        "action": "rerequested",
        "check_run": {
            "name": githubapp.CHECK_NAME,
            "head_sha": "c" * 40,
            "check_suite": {"head_repository": {"owner": {"login": "fork-owner"}}},
        },
    }
    rerun_job = githubapp.job("check_run", rerun) or {}
    if rerun_job.get("base_sha", "missing") is not None or rerun_job.get("owner") != "fork-owner":
        raise SystemExit(f"FAIL rerequested check run did not preserve its head owner: {rerun_job}")
    missing_head = {**rerun, "check_run": {"name": githubapp.CHECK_NAME, "head_sha": "d" * 40}}
    if (githubapp.job("check_run", missing_head) or {}).get("owner", "missing") != "":
        raise SystemExit("FAIL a rerequest with no head-repository identity inherited the trusted base owner")
    other = {**rerun, "check_run": {"name": "someone else", "head_sha": "c" * 40}}
    if githubapp.job("check_run", other) is not None or githubapp.job("push", common) is not None:
        raise SystemExit("FAIL another App's check run or an unasked event was queued")
    saved = os.environ.get("THEA_APP_RUN_OWNERS")
    try:
        os.environ["THEA_APP_RUN_OWNERS"] = "Example-Org, other"
        verdicts = (githubapp.allowed("example-org", "example-org/r"), githubapp.allowed("fork-owner", "example-org/r"))
        os.environ["THEA_APP_RUN_OWNERS"] = ""
        verdicts += (githubapp.allowed("example-org", "example-org/r"),)
    finally:
        os.environ.pop("THEA_APP_RUN_OWNERS", None) if saved is None else os.environ.__setitem__(
            "THEA_APP_RUN_OWNERS", saved
        )
    if verdicts != (True, False, False):
        raise SystemExit(f"FAIL allowlist (owner, fork, empty) = {verdicts}, want (True, False, False)")
    CASES.append(
        (
            "events: check_suite/check_run/pull_request queue a head; forks and unlisted owners never run",
            "a stranger's PR runs on the host",
        )
    )



def run_verify_tree_case(work: Path) -> None:
    """The service must execute the checked-out head's verifier with that tree as THEA_ROOT."""
    import githubapp

    tree = work / "verify-tree"
    (tree / "scripts").mkdir(parents=True)
    (tree / "atlas.yaml").write_text("version: fixture\n", encoding="utf-8")
    (tree / "scripts" / "verify.py").write_text("raise SystemExit('the fixture is not executed')\n", encoding="utf-8")
    seen: dict = {}
    saved = githubapp.subprocess.run

    def fake(argv, **kwargs):
        seen.update({"argv": argv, **kwargs})
        payload = {"tally": {"PASS": 1}, "rows": [{"id": "fixture", "verdict": "PASS"}]}
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

    githubapp.subprocess.run = fake
    try:
        result = githubapp.run_verify("b" * 40, tree)
    finally:
        githubapp.subprocess.run = saved
    if (
        Path(seen["argv"][1]) != tree / "scripts" / "verify.py"
        or seen["env"].get("THEA_ROOT") != str(tree)
        or seen["env"].get("THEA_BASE") != "b" * 40
        or result["exit"] != 0
    ):
        raise SystemExit(f"FAIL verify did not target the checked-out head: {seen}, {result}")
    CASES.append(("the GitHub App runs the checked-out head's verifier with THEA_ROOT set", "a green check for the host tree"))



def _openssl(*args: str, data: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["openssl", *args], input=data, capture_output=True, check=False, timeout=TIMEOUT)  # noqa: S603


def _b64d(part: str) -> bytes:
    import base64

    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _test_key(work: Path) -> Path:
    key = work / "app.pem"
    if not key.exists() and _openssl("genrsa", "-out", str(key), "2048").returncode != 0:
        raise SystemExit("FAIL openssl genrsa could not make a test key")
    return key


def jwt_case(work: Path) -> None:
    import base64

    import githubapp

    key = _test_key(work)
    token = githubapp.app_jwt("12345", base64.b64encode(key.read_bytes()).decode(), now=1_700_000_000)
    header, claims, signature = token.split(".")
    if json.loads(_b64d(header)) != {"alg": "RS256", "typ": "JWT"}:
        raise SystemExit(f"FAIL JWT header {_b64d(header)!r}")
    body = json.loads(_b64d(claims))
    if body != {"iat": 1_700_000_000 - 60, "exp": 1_700_000_000 + 540, "iss": "12345"}:
        raise SystemExit(f"FAIL JWT claims {body}")
    public = work / "app.pub"
    _openssl("rsa", "-in", str(key), "-pubout", "-out", str(public))
    sig = work / "sig.bin"
    sig.write_bytes(_b64d(signature))
    signed = f"{header}.{claims}".encode()
    if _openssl("dgst", "-sha256", "-verify", str(public), "-signature", str(sig), data=signed).returncode != 0:
        raise SystemExit("FAIL the app JWT does not verify against its own public key")
    if _openssl("dgst", "-sha256", "-verify", str(public), "-signature", str(sig), data=signed + b"x").returncode == 0:
        raise SystemExit("FAIL openssl verified a tampered JWT — the JWT proof proves nothing")
    if githubapp.urllib_transport("GET", (work / "app.pub").as_uri(), {}, None)[0] != 0:
        raise SystemExit("FAIL the live transport opened a file: URL — THEA_GITHUB_API must be https")
    CASES.append(("app JWT is RS256 over iat/exp/iss and verifies with openssl", "a token GitHub rejects on install"))


def queue_case(work: Path) -> None:
    from githubapp import Queue

    queue = Queue(work / "queue-case")
    job = {"repo": "o/r", "head_sha": "a" * 40, "base_sha": "b" * 40, "installation_id": 1, "pr": 1}
    if not queue.enqueue(job) or queue.enqueue(dict(job)) or queue.enqueue({**job, "base_sha": "c" * 40}):
        raise SystemExit("FAIL the queue is not idempotent on (repo, head sha)")
    first = queue.claim()
    if not first or queue.claim() is not None:
        raise SystemExit("FAIL one pending job was claimed twice or not at all")
    if not queue.release(first, "transient") or queue.counts() != {"pending": 1, "running": 0, "done": 0}:
        raise SystemExit(f"FAIL release did not return the job to pending: {queue.counts()}")
    again = queue.claim() or {}
    if queue.recover(lease=0, now=float("inf")) != 1 or int(again.get("attempts") or 0) != 1:
        raise SystemExit("FAIL an expired lease was not recovered to pending")
    queue.complete(queue.claim() or {}, {"verdict": "PASS"})
    if queue.enqueue(dict(job)) or not queue.requeue(dict(job)) or queue.requeue(dict(job)):
        raise SystemExit("FAIL a done head must refuse enqueue, accept one rerequest, refuse a second while pending")
    CASES.append(
        (
            "queue: idempotent per (repo, sha), one claimant, release, lease recovery, rerequest",
            "double runs, lost jobs",
        )
    )


def batch_case() -> None:
    import githubapp

    notes = [{"path": f"f{i}.py", "message": "m"} for i in range(120)]
    sizes = [len(b) for b in githubapp.annotation_batches(notes)]
    if sizes != [50, 50, 20] or githubapp.annotation_batches([]) != [[]]:
        raise SystemExit(f"FAIL annotation batches {sizes}; GitHub refuses more than 50 per request")
    CASES.append(("annotations go in batches of at most 50, and an empty run still completes", "a 422 on big PRs"))


class FakeGitHub:
    """Records every call; answers the three endpoints the flow uses. No network."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict]:
        path = url.split("://", 1)[-1].split("/", 1)[-1]
        self.calls.append(
            {
                "method": method,
                "path": "/" + path,
                "auth": headers["Authorization"],
                "body": json.loads(body or b"null"),
            }
        )
        if path.endswith("/access_tokens"):
            return 201, {"token": "ghs_fixture-installation-token"}
        if method == "POST" and path.endswith("/check-runs"):
            return 201, {"id": 77}
        if method == "PATCH" and "/check-runs/" in path:
            return 200, {"id": 77}
        return 404, {"message": "not recorded"}



def finish_give_up_case(work: Path) -> None:
    """An exhausted job completes an existing check run as neutral before its queue record becomes done."""
    import githubapp

    queue = githubapp.Queue(work / "give-up")
    original = {
        "repo": "example-org/example-repo",
        "head_sha": "a" * 40,
        "base_sha": "b" * 40,
        "installation_id": 4242,
        "pr": 7,
        "owner": "example-org",
    }
    queue.enqueue(original)
    claimed = queue.claim() or {}
    claimed["check_run_id"] = 77
    fake = FakeGitHub()
    result = githubapp.finish_give_up(claimed, queue, fake, lambda installation_id: "ghs_fixture")
    patches = [call for call in fake.calls if call["method"] == "PATCH"]
    if (
        result.get("conclusion") != "neutral"
        or queue.counts() != {"pending": 0, "running": 0, "done": 1}
        or len(patches) != 1
        or patches[0]["body"].get("status") != "completed"
        or patches[0]["body"].get("conclusion") != "neutral"
    ):
        raise SystemExit(f"FAIL exhausted check was not completed neutral: {result}, {queue.counts()}, {patches}")
    CASES.append(("an exhausted job completes its existing check run as neutral", "a permanent in-progress check"))



def _git(tree: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=tree, capture_output=True, text=True, check=False, timeout=TIMEOUT)  # noqa: S603
    if done.returncode != 0:
        raise SystemExit(f"FAIL git {' '.join(args)}: {done.stderr}")
    return done.stdout.strip()


def _origin(work: Path) -> tuple[Path, str, str]:
    origin = work / "origin"
    origin.mkdir()
    _git(origin, "init", "--quiet", "-b", "main")
    _git(origin, "config", "user.email", "fixture@example.invalid")
    _git(origin, "config", "user.name", "fixture")
    (origin / "app.py").write_text("print('hello')\n", encoding="utf-8")
    _git(origin, "add", "app.py")
    _git(origin, "commit", "--quiet", "-m", "base")
    base = _git(origin, "rev-parse", "HEAD")
    _git(origin, "checkout", "--quiet", "-b", "topic")
    (origin / "app.py").write_text("print('hello, world')\n", encoding="utf-8")
    _git(origin, "commit", "--quiet", "-am", "head")
    return origin, base, _git(origin, "rev-parse", "HEAD")


def _fixture(name: str, **subs: str) -> bytes:
    text = (ROOT / FIXTURES / name).read_text(encoding="utf-8")
    for key, value in subs.items():
        text = text.replace(key, value)
    return text.encode()


def _deliver(queue, event: str, body: bytes, signature: str | None = None) -> tuple[int, dict]:
    import githubapp

    headers = {"X-GitHub-Event": event, "X-GitHub-Delivery": "fixture-delivery"}
    headers["X-Hub-Signature-256"] = signature if signature is not None else _sign(body)
    return githubapp.handle(headers, body, SECRET, queue)


def _ingest(queue, opened: bytes) -> None:
    """A forged delivery is refused before queueing; a redelivery is a no-op; installs are recorded."""
    if (
        _deliver(queue, "pull_request", opened, signature=_sign(opened, "forged"))[0] != 401
        or queue.counts()["pending"]
    ):
        raise SystemExit("FAIL a forged delivery was not refused with 401 before queueing")
    if _deliver(queue, "pull_request", opened)[0] != 202 or _deliver(queue, "pull_request", opened)[0] != 200:
        raise SystemExit("FAIL first delivery must queue (202), the redelivery must be a no-op (200)")
    if _deliver(queue, "installation", _fixture("installation_created.json"))[0] != 200:
        raise SystemExit("FAIL installation event not recorded")


def _drain(queue, work: Path) -> FakeGitHub:
    """Drain the queue against a fake GitHub with canned verify rows; env and run_verify are restored."""
    import base64

    import githubapp

    # The gate run is the one seam replaced: verify itself is proven by its own suite, and running it here
    # would run this suite inside itself. Everything around it — diff, report, mapping — is the real code.
    canned = {
        "exit": 1,
        "stderr_tail": "",
        "verify": {
            "rows": [
                {"id": "unit_tests:app.py", "verdict": "FAIL", "why": "1 failed, 3 passed"},
                {"id": "formatter:app.py", "verdict": "NOT RUN", "why": "ruff is not installed here"},
                {"id": "contract", "verdict": "PASS", "why": ""},
            ],
            "tally": {"PASS": 1, "FAIL": 1, "NOT RUN": 1},
        },
    }
    env = {
        "THEA_GITHUB_APP_ID": "12345",
        "THEA_GITHUB_APP_PRIVATE_KEY_B64": base64.b64encode(_test_key(work).read_bytes()).decode(),
        "THEA_APP_RUN_OWNERS": "example-org",
    }
    saved_verify, saved_env = githubapp.run_verify, {k: os.environ.get(k) for k in env}
    githubapp.run_verify = lambda base_sha, tree=None: canned
    os.environ.update(env)
    fake = FakeGitHub()
    try:
        tally = githubapp.drain(queue, fake, githubapp.env_tokens(fake))
    finally:
        githubapp.run_verify = saved_verify
        for key, value in saved_env.items():
            os.environ.pop(key, None) if value is None else os.environ.__setitem__(key, value)
    if tally != {"done": 1, "retried": 0, "gave_up": 0}:
        raise SystemExit(f"FAIL drain tally {tally}; done/ holds {queue.counts()}")
    return fake


def _check_calls(fake: FakeGitHub, head: str) -> None:
    """Token, check run in_progress, fresh token, PATCH completed as failure with per-file annotations."""
    import githubapp

    sequence = [(c["method"], c["path"]) for c in fake.calls]
    want = [
        ("POST", "/app/installations/4242/access_tokens"),
        ("POST", "/repos/example-org/example-repo/check-runs"),
        ("POST", "/app/installations/4242/access_tokens"),  # fresh token: a suite can outlive the first
        ("PATCH", "/repos/example-org/example-repo/check-runs/77"),
    ]
    if sequence != want:
        raise SystemExit(f"FAIL API sequence {sequence}, want {want}")
    if fake.calls[0]["auth"].count(".") != 2 or "ghs_fixture" not in fake.calls[1]["auth"]:
        raise SystemExit("FAIL the token exchange must use the app JWT, the check run the installation token")
    started, finished = fake.calls[1]["body"], fake.calls[3]["body"]
    if (started["status"], started["head_sha"], started["name"]) != ("in_progress", head, githubapp.CHECK_NAME):
        raise SystemExit(f"FAIL check run did not start in_progress on the head: {started}")
    if finished.get("status") != "completed" or finished.get("conclusion") != "failure":
        raise SystemExit(f"FAIL check run did not complete as failure: {finished}")
    notes = finished["output"]["annotations"]
    messages = sorted(n["message"] for n in notes)
    if [n["path"] for n in notes] != ["app.py", "app.py"] or not any(
        "skipped its required gate `formatter`" in m for m in messages
    ):
        raise SystemExit(f"FAIL per-file annotations {notes}")


def _check_timeline(queue, head: str, subs: dict) -> None:
    """The done record, the refusal row, then a merge of the refused head records an override."""
    result = queue.result("example-org/example-repo", head) or {}
    if result.get("changed_files") != ["app.py"] or result.get("check_run_id") != 77:
        raise SystemExit(f"FAIL done record {result}")
    rows = queue.timeline_rows()
    if (
        len(rows) != 1
        or rows[0]["kind"] != "refusal"
        or {b["gate"] for b in rows[0]["blocked"]} != {"unit_tests", "formatter"}
    ):
        raise SystemExit(f"FAIL refusal timeline {rows}")
    merged = _fixture("pull_request_closed_merged.json", **subs)
    if _deliver(queue, "pull_request", merged)[1] != {"override": True}:
        raise SystemExit("FAIL merging a refused head did not record an override")
    rows = queue.timeline_rows()
    if [r["kind"] for r in rows] != ["refusal", "override"] or rows[1]["actor"] != "example-admin":
        raise SystemExit(f"FAIL override timeline {rows}")


def end_to_end_case(work: Path) -> None:
    """webhook -> queue -> runner (real checkout + build_report) -> fake GitHub -> timeline, then an override."""
    from githubapp import Queue

    origin, base, head = _origin(work)
    subs = {"HEAD_SHA": head, "BASE_SHA": base, "CLONE_URL": str(origin), "MERGE_SHA": "f" * 40}
    queue = Queue(work / "state")
    _ingest(queue, _fixture("pull_request_opened.json", **subs))
    _check_calls(_drain(queue, work), head)
    _check_timeline(queue, head, subs)
    CASES.append(
        (
            "end to end: signed webhook -> queue -> checkout + build_report -> check run on a fake GitHub -> timeline",
            "an App whose pieces each pass while the flow between them was never run",
        )
    )
