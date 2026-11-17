#!/usr/bin/env python3
"""Where a measurement may send a prompt: OpenAI-compatible endpoints, their key NAMES, their pace.

WHY (2.28.0). The A/B had been measured on three models behind one local router — a fact about three
models. Breadth across model families is what turns it into a claim, and every provider below speaks
the same chat-completions shape, so one harness reaches all of them.

KEYS ARE READ FROM THE PROCESS ENVIRONMENT ONLY, by NAME, and never printed, logged or written. This
repository is public: no key value, no local key-file path, no account id appears in it. The caller
loads its own keys (`set -a; . <your key file>`) before running. A missing key is REFUSED by name.

THE PACE IS DECLARED, NOT DISCOVERED. `rpm` is a conservative per-process request rate. A 429 that
gets through means the declared pace is too high — lower it here; never answer it with more retries.
A 402 means the window's budget is gone, and resilience latches the breaker for the run.

WHAT IT DOES NOT PROVE. That siblings on the same credential back off: a vendor sees the SUM of every
process on a key. Prefer a key no other job holds; the NVIDIA entry skips the first key for that reason.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import atomicfile
import resilience

# OFFLINE BY DEFAULT. A measurement replays a recorded answer when one exists, and refuses with
# ReplayMiss when none does; it reaches a vendor only when the run asks for --live (set_live) or
# HEADRON_PROVIDERS_LIVE=1. A replay never needs a key, so CI and reruns cost nothing and stay deterministic.
LIVE = os.environ.get("HEADRON_PROVIDERS_LIVE") == "1"


class ReplayMiss(ValueError):  # a ValueError, so each caller's existing REFUSED path already reports it
    """No recording for this question, and offline mode is on. Run once with --live to record it."""


def set_live(on: bool) -> None:
    global LIVE
    LIVE = on


def replay_dir() -> Path:
    """Recordings live OUTSIDE the repository: an answer is derived from a vendor, not a tracked file."""
    return Path(os.environ.get("HEADRON_REPLAY_DIR") or Path.home() / ".cache" / "headron" / "replay")


# MATCHES A BARE CHAT ENDPOINT, CHOSEN AFTER SEEING THE OUTCOME — so it is declared, and counted.
# MEASURED at 2.28.0 with "Answer briefly.": Sonnet scored 30/39 given the gate, and 8 of its 9 misses
# were not wrong answers but attempts to CALL A TOOL ("read_file languages/v/OPERATING.md") — the CLI's
# residual preamble primes an agent, where an HTTP provider offers no tools at all. Those rows measured
# the harness, not the model. Every Claude row is re-run under this prompt; none is mixed across the two.
_CLI_SYSTEM = "You have no tools and cannot read files. Answer only from the text you are given, briefly."

PROVIDERS: dict[str, dict] = {
    # ANY LOCAL OPENAI-COMPATIBLE ROUTER, at the address its owner sets — Headron names no particular one.
    "router": {
        "url": os.environ.get("HEADRON_ROUTER_URL", "http://127.0.0.1:8799/v1/chat/completions"),
        "headers": {"X-Client": "antigravity"},
        "keys": [],
        "rpm": 120,
    },
    "ollama": {"url": "http://127.0.0.1:11434/v1/chat/completions", "keys": [], "rpm": 20},
    "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions", "keys": ["OPENROUTER_API_KEY"], "rpm": 6},
    "nvidia": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "keys": ["NVIDIA_API_KEY_4", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3"],
        "rpm": 30,
    },
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "keys": ["GROQ_API_KEY"], "rpm": 25},
    "cerebras": {"url": "https://api.cerebras.ai/v1/chat/completions", "keys": ["CEREBRAS_API_KEY"], "rpm": 25},
    "sambanova": {"url": "https://api.sambanova.ai/v1/chat/completions", "keys": ["SAMBANOVA_API_KEY"], "rpm": 15},
    "mistral": {"url": "https://api.mistral.ai/v1/chat/completions", "keys": ["MISTRAL_API_KEY"], "rpm": 40},
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "keys": ["GEMINI_API_KEY"],
        "rpm": 10,
    },
    "together": {"url": "https://api.together.xyz/v1/chat/completions", "keys": ["TOGETHER_API_KEY"], "rpm": 30},
    "huggingface": {
        "url": "https://router.huggingface.co/v1/chat/completions",
        "keys": ["HUGGINGFACE_API_KEY"],
        "rpm": 20,
    },
    "cloudflare": {
        "url": "https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions",
        "keys": ["CLOUDFLARE_API_TOKEN"],
        "rpm": 60,
    },
    # THE KILO GATEWAY, as the first external freebench run reached it. Its listing flags each free
    # model (`isFree`); those answer without a key. Every other model on it bills the key.
    "kilo": {
        "url": "https://api.kilo.ai/api/gateway/v1/chat/completions",
        "models_url": "https://api.kilo.ai/api/gateway/models",
        "url_keys": ["HEADRON_KILO_URL", "KILO_BASE_URL"],
        "keys": ["KILOCODE_API_KEY", "KILO_API_KEY"],
        "optional_key": True,
        "rpm": 20,
    },
    "kaggle": {
        "url": "https://api.kaggle.com/v1/chat/completions",
        "keys": ["KAGGLE_API_TOKEN", "KAGGLE_KEY"],
        "rpm": 30,
    },
    "google-ai-studio": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "keys": ["GOOGLE_AI_STUDIO_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"],
        "rpm": 30,
    },
    # CLAUDE THROUGH THE CLAUDE CODE CLI, on whatever login that CLI holds — no key here. The A/B had
    # 8 models on 4 providers and NOT ONE was Claude, the runtime this contract is written for first.
    # Bedrock was probed first and refused (the IAM user may not invoke models); the CLI reaches the
    # same models and is how Claude Code itself reaches them. See `_claude_cli` for the token math.
    "claude-cli": {
        "cli": [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--tools",
            "",
            "--setting-sources",
            "",
            "--no-session-persistence",
            "--strict-mcp-config",
            "--system-prompt",
            _CLI_SYSTEM,
        ],
        "keys": [],
        "rpm": 30,
    },
}


def endpoint(name: str) -> tuple[str, dict[str, str]]:
    """(url, headers) for a provider, or ValueError naming what is missing — never a key's value."""
    spec = PROVIDERS.get(name)
    if spec is None:
        raise ValueError(f"unknown provider {name!r}; declared: {', '.join(sorted(PROVIDERS))}")
    url = spec["url"]
    if "url_keys" in spec:
        for k in spec["url_keys"]:
            if os.environ.get(k):
                val = os.environ[k].rstrip("/")
                url = f"{val}/chat/completions" if not val.endswith("/chat/completions") else val
                break
    for field in ("CLOUDFLARE_ACCOUNT_ID",):
        if "{" + field + "}" in url:
            if not os.environ.get(field):
                raise ValueError(f"provider {name} needs {field} in the environment")
            url = url.replace("{" + field + "}", os.environ[field])
    # A NAMED CLIENT. MEASURED at 2.28.0: Groq, Cerebras and Together all answered 403 to urllib's
    # default `Python-urllib/3.x` — the same refusal from three vendors behind the same bot filter,
    # which is a fact about the client, not about the keys.
    headers = {"Content-Type": "application/json", "User-Agent": "headron-atlas-abtest/1.0"}
    if "headers" in spec:
        headers.update(spec["headers"])
    if spec["keys"]:
        key = next((os.environ[k] for k in spec["keys"] if os.environ.get(k)), None)
        if key is None and not spec.get("optional_key"):
            raise ValueError(f"provider {name} needs one of {spec['keys']} in the environment")
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
    return url, headers


def probe_provider(name: str, timeout: float = 2.0) -> bool:
    """Non-throwing health check: whether a provider is configured and responding."""
    spec = PROVIDERS.get(name)
    if spec is None:
        return False
    if "cli" in spec:
        import shutil  # noqa: PLC0415

        return shutil.which(spec["cli"][0]) is not None
    try:
        url, headers = endpoint(name)
        req = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout):  # noqa: S310
            return True
    except urllib.error.HTTPError as err:
        return err.code in (400, 404, 405)
    except (OSError, ValueError):
        return False
    return False


def available_providers(timeout: float = 2.0) -> list[str]:
    """List of all registered providers that are currently configured and reachable."""
    return [name for name in PROVIDERS if probe_provider(name, timeout=timeout)]


def resolve_fallback(chain: list[str], timeout: float = 2.0) -> str | None:
    """Find the first reachable provider from a priority chain."""
    for name in chain:
        if probe_provider(name, timeout=timeout):
            return name
    return None


def list_models(name: str, timeout: float = 20.0) -> list[dict]:
    """[{id, free}] from a provider's model listing; `free` is None where the listing carries no flag.

    A LISTING IS NOT A MODEL THAT ANSWERS: an id here is a candidate until `canary` drives a request through it."""
    url, headers = endpoint(name)
    url = PROVIDERS[name].get("models_url") or url.replace("/chat/completions", "/models")
    request = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310 — declared endpoints
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.load(response)
    rows = payload.get("data", []) if isinstance(payload, dict) else payload
    return [
        {"id": str(m["id"]), "free": m["isFree"] if isinstance(m.get("isFree"), bool) else None}
        for m in rows
        if isinstance(m, dict) and m.get("id")
    ]


def identity(requested: str, served: object) -> str:
    """match | differs | unreported. A router lane serves some OTHER model under its own name, so a
    record is named by what answered, never by what was asked for (`a_chain_lane_read_as_a_model`)."""
    if not isinstance(served, str) or not served.strip():
        return "unreported"
    want, got = requested.lower().split(":")[0], served.lower().split(":")[0]
    tail = lambda s: s.rsplit("/", 1)[-1]  # noqa: E731 — vendors add or drop an org prefix
    return "match" if tail(got) == tail(want) or tail(got).startswith(tail(want)) else "differs"


CANARY = "Reply with exactly this token and nothing else: HEADRON-{n}"


def canary(name: str, model: str, timeout: int = 60, max_tokens: int = 400) -> dict:
    """One live request through one model: whether it answered, what served it, how long it took.

    ONE ATTEMPT, NO RETRY, NO REPLAY: a census records the lane as it is now. A refusal of any kind is
    `not_run` with its class, never a wrong answer — the transport failed, the model was not asked."""
    n = int(hashlib.sha256(f"{name}/{model}".encode()).hexdigest()[:6], 16) % 10000
    token = f"HEADRON-{n}"
    row: dict = {"provider": name, "model": model, "status": "not_run", "error": None, "served": None}
    try:
        url, headers = endpoint(name)
        _PACERS.setdefault(name, resilience.Pacer(PROVIDERS[name]["rpm"])).wait()
        body = {"model": model, "temperature": 0, "max_tokens": max_tokens}
        body["messages"] = [{"role": "user", "content": CANARY.format(n=n)}]
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)  # noqa: S310
        t0 = time.monotonic()
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.load(response)
        row["seconds"] = round(time.monotonic() - t0, 2)
        resilience.answer_or_refuse(name, payload, ("choices.0.message.content",))
    except (OSError, ValueError, KeyError, resilience.BreakerOpen) as err:
        status = getattr(err, "code", None)
        row["error"] = f"{resilience.classify(error=err)}:{status or type(err).__name__}"
        return row
    answer = str(payload["choices"][0]["message"]["content"] or "")
    usage = payload.get("usage") or {}
    row.update(
        status="alive",
        served=payload.get("model"),
        identity=identity(model, payload.get("model")),
        followed=answer.strip().strip(".`'\"") == token,
        tokens_out=usage.get("completion_tokens"),
    )
    return row


def census(names: list[str], free_only: bool = True, limit: int | None = None) -> list[dict]:
    """Every listed model on each named provider, canaried once. With `free_only`, a listing that FLAGS
    price keeps only its free models; a listing with no flag is kept whole (its key's tier decides)."""
    rows: list[dict] = []
    for name in names:
        try:
            listed = list_models(name)
        except (OSError, ValueError, KeyError) as err:
            rows.append({"provider": name, "model": None, "status": "not_run", "error": f"listing:{err}"[:160]})
            continue
        keep = [m for m in listed if not free_only or m["free"] is not False][:limit]
        rows += [{**canary(name, m["id"]), "free": m["free"]} for m in keep]
    return rows


_PACERS: dict[str, resilience.Pacer] = {}
_BREAKERS: dict[str, resilience.Breaker] = {}


def _replay_key(provider: str, model: str, prompt: str, max_tokens: int) -> str:
    """The question's identity. Timeout is left out: it changes how long we wait, not what is asked."""
    text = json.dumps(
        {"v": 1, "provider": provider, "model": model, "prompt": prompt, "max_tokens": max_tokens}, sort_keys=True
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _replay_write(key: str, provider: str, model: str, answer: str, tokens: int | None) -> None:
    if not answer:  # an empty answer is UNANSWERED (see _live), never a fact to replay
        return
    directory = replay_dir()
    directory.mkdir(parents=True, exist_ok=True)
    row = {"provider": provider, "model": model, "answer": answer, "tokens": tokens}
    atomicfile.write_text(directory / f"{key}.json", json.dumps(row))


def complete(provider: str, model: str, prompt: str, timeout: int, max_tokens: int = 120) -> tuple[str, int | None]:
    """(answer, prompt_tokens or None). Replays a recording when one exists; live only when LIVE is set.

    A live answer is recorded, so the next run of the same question is offline. An empty answer is not."""
    key = _replay_key(provider, model, prompt, max_tokens)
    path = replay_dir() / f"{key}.json"
    if path.is_file():
        row = json.loads(path.read_text(encoding="utf-8"))
        return str(row["answer"]), row["tokens"]
    if not LIVE:
        raise ReplayMiss(
            f"no recording for {provider}/{model} (key {key[:12]}) and offline mode is on; run with --live once"
        )
    answer, tokens = _live(provider, model, prompt, timeout, max_tokens)
    _replay_write(key, provider, model, answer, tokens)
    return answer, tokens


def _live(provider: str, model: str, prompt: str, timeout: int, max_tokens: int = 120) -> tuple[str, int | None]:
    """(answer, prompt_tokens or None). A server that reports no usage gets None — never an estimate.

    A REASONING MODEL SPENDS ITS OUTPUT CAP BEFORE IT ANSWERS. MEASURED at 2.28.0: gpt-oss-120b used
    78 of 88 completion tokens reasoning on a one-word question, so at a 120 cap a longer prompt
    returns EMPTY content, which a substring scorer reads as a wrong answer. The caller counts an
    empty answer as UNANSWERED, never as wrong, and raises `max_tokens` for that model."""
    if "cli" in PROVIDERS.get(provider, {}):
        return _claude_cli(provider, model, prompt, timeout)
    url, headers = endpoint(provider)
    pacer = _PACERS.setdefault(provider, resilience.Pacer(PROVIDERS[provider]["rpm"]))
    breaker = _BREAKERS.setdefault(provider, resilience.Breaker(threshold=3, cooldown=60.0))
    body = json.dumps(
        {"model": model, "temperature": 0, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    ).encode()

    def once() -> dict:
        pacer.wait()
        request = urllib.request.Request(url, data=body, headers=headers)  # noqa: S310 — declared endpoints
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.load(response)

    payload = resilience.call(once, attempts=3, base=2.0, cap=30.0, deadline=timeout * 3.0, breaker=breaker)
    # A 200 CARRYING AN ERROR BODY, or carrying nothing at all. One predicate for every answer path
    # in this file (resilience.missing): the copy that lived here refused an absent `choices` and the
    # CLI copy did not refuse an empty result, which is the same rule with a clause missing.
    resilience.answer_or_refuse(provider, payload, ("choices.0.message.content",))
    usage = payload.get("usage") or {}
    tokens = usage.get("prompt_tokens")
    return str(payload["choices"][0]["message"]["content"] or ""), int(tokens) if tokens is not None else None


_CLI_OVERHEAD: dict[str, int] = {}


def _cli_once(provider: str, model: str, prompt: str, timeout: int) -> tuple[str, int]:
    import subprocess
    import tempfile

    _PACERS.setdefault(provider, resilience.Pacer(PROVIDERS[provider]["rpm"])).wait()
    # AN EMPTY DIRECTORY, so no project CLAUDE.md or settings reaches the prompt: the arm under test
    # is the ONLY context the model sees, as it is for every HTTP provider.
    with tempfile.TemporaryDirectory() as cwd:
        done = subprocess.run(
            [*PROVIDERS[provider]["cli"], "--model", model],
            input=prompt,
            cwd=cwd,  # noqa: S603
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    try:
        out = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{provider} printed no JSON (exit {done.returncode}): {done.stderr.strip()[:160]}") from exc
    if out.get("is_error"):
        raise ValueError(f"{provider} refused: {str(out.get('result'))[:160]}")
    # EXIT 0 IS A RENDERING TOO. Without this, a run that produced nothing returned "" with a token
    # count beside it, and a non-answer was scored as a wrong answer.
    resilience.answer_or_refuse(provider, out, ("result",))
    u = out.get("usage") or {}
    # Cached input is still input the model read: a repeated long arm hits the cache, and dropping
    # the cached part would credit the ARM with the cache's saving.
    read = (
        int(u.get("input_tokens", 0))
        + int(u.get("cache_read_input_tokens", 0))
        + int(u.get("cache_creation_input_tokens", 0))
    )
    return str(out.get("result") or ""), read


def _claude_cli(provider: str, model: str, prompt: str, timeout: int) -> tuple[str, int | None]:
    """(answer, prompt_tokens) through the Claude Code CLI.

    THE CLI ADDS A FIXED PREAMBLE TO EVERY CALL. MEASURED at 2.28.0: 552-555 input tokens for a
    one-character prompt on Haiku, 553 for a five-word one. Left in, that constant lands on every arm alike and drags every
    "% fewer" ratio toward zero — a friendlier number for the cheap arm's rival, measured by
    nothing. So it is CALIBRATED once per model (a one-character prompt) and subtracted; the
    residual error is the calibration prompt's own ~1 token, the same on every arm."""
    if model not in _CLI_OVERHEAD:
        _CLI_OVERHEAD[model] = max(_cli_once(provider, model, ".", timeout)[1] - 1, 0)
    answer, read = _cli_once(provider, model, prompt, timeout)
    return answer, max(read - _CLI_OVERHEAD[model], 0)


def main(argv: list[str] | None = None) -> int:
    """`providers.py` lists each provider and whether its key NAME is set — values are never shown.

    `providers.py --census groq,kilo [--all-prices] [--limit N] [--out FILE]` canaries every listed model
    once and writes the rows as JSON (outside the repository: a census is derived from vendors)."""
    argv = sys.argv[1:] if argv is None else argv
    if "--census" in argv:
        names = argv[argv.index("--census") + 1].split(",")
        limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
        rows = census(names, free_only="--all-prices" not in argv, limit=limit)
        for name in names:
            mine = [r for r in rows if r["provider"] == name]
            alive = [r for r in mine if r["status"] == "alive"]
            print(
                f"  {name:<11} listed-and-asked {len(mine):<4} alive {len(alive):<4} followed "
                f"{sum(bool(r.get('followed')) for r in alive):<4} served-as-other "
                f"{sum(r.get('identity') == 'differs' for r in alive)}"
            )
        if "--out" in argv:
            atomicfile.write_text(Path(argv[argv.index("--out") + 1]), json.dumps(rows, indent=1) + "\n")
        return 0 if any(r["status"] == "alive" for r in rows) else 1
    for name, spec in sorted(PROVIDERS.items()):
        ready = not spec["keys"] or any(os.environ.get(k) for k in spec["keys"])
        print(
            f"  {'ready ' if ready else 'no key'} {name:<11} rpm {spec['rpm']:<4} keys {', '.join(spec['keys']) or '(none)'}"
        )
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    raise SystemExit(main())
