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

import json
import os
import urllib.request

import resilience

# PARITY WITH A BARE CHAT ENDPOINT, CHOSEN AFTER SEEING THE OUTCOME — so it is declared, and counted.
# MEASURED at 2.28.0 with "Answer briefly.": Sonnet scored 30/39 given the gate, and 8 of its 9 misses
# were not wrong answers but attempts to CALL A TOOL ("read_file languages/v/OPERATING.md") — the CLI's
# residual preamble primes an agent, where an HTTP provider offers no tools at all. Those rows measured
# the harness, not the model. Every Claude row is re-run under this prompt; none is mixed across the two.
_CLI_SYSTEM = "You have no tools and cannot read files. Answer only from the text you are given, briefly."

PROVIDERS: dict[str, dict] = {
    "freeroute": {"url": "http://127.0.0.1:8799/v1/chat/completions", "keys": [], "rpm": 120},
    "ollama": {"url": "http://127.0.0.1:11434/v1/chat/completions", "keys": [], "rpm": 20},
    "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions", "keys": ["OPENROUTER_API_KEY"], "rpm": 6},
    "nvidia": {"url": "https://integrate.api.nvidia.com/v1/chat/completions",
               "keys": ["NVIDIA_API_KEY_4", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3"], "rpm": 30},
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "keys": ["GROQ_API_KEY"], "rpm": 25},
    "cerebras": {"url": "https://api.cerebras.ai/v1/chat/completions", "keys": ["CEREBRAS_API_KEY"], "rpm": 25},
    "sambanova": {"url": "https://api.sambanova.ai/v1/chat/completions", "keys": ["SAMBANOVA_API_KEY"], "rpm": 15},
    "mistral": {"url": "https://api.mistral.ai/v1/chat/completions", "keys": ["MISTRAL_API_KEY"], "rpm": 40},
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
               "keys": ["GEMINI_API_KEY"], "rpm": 10},
    "together": {"url": "https://api.together.xyz/v1/chat/completions", "keys": ["TOGETHER_API_KEY"], "rpm": 30},
    # USED ONLY WHILE DELTAHOOD IS PAUSED: its key's quota is otherwise that project's, and a vendor
    # sees the sum of every process on a credential. The owner paused Deltahood for these runs.
    "openrouter-deltahood": {"url": "https://openrouter.ai/api/v1/chat/completions",
                             "keys": ["DELTAHOOD_OPENROUTER_API_KEY"], "rpm": 15},
    "huggingface": {"url": "https://router.huggingface.co/v1/chat/completions", "keys": ["HUGGINGFACE_API_KEY"], "rpm": 20},
    "cloudflare": {"url": "https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions",
                   "keys": ["CLOUDFLARE_API_TOKEN"], "rpm": 60},
    # CLAUDE THROUGH THE CLAUDE CODE CLI, on whatever login that CLI holds — no key here. The A/B had
    # 8 models on 4 providers and NOT ONE was Claude, the runtime this contract is written for first.
    # Bedrock was probed first and refused (the IAM user may not invoke models); the CLI reaches the
    # same models and is how Claude Code itself reaches them. See `_claude_cli` for the token math.
    "claude-cli": {"cli": ["claude", "-p", "--output-format", "json", "--tools", "", "--setting-sources", "",
                           "--no-session-persistence", "--strict-mcp-config", "--system-prompt", _CLI_SYSTEM],
                   "keys": [], "rpm": 30},
}


def endpoint(name: str) -> tuple[str, dict[str, str]]:
    """(url, headers) for a provider, or ValueError naming what is missing — never a key's value."""
    spec = PROVIDERS.get(name)
    if spec is None:
        raise ValueError(f"unknown provider {name!r}; declared: {', '.join(sorted(PROVIDERS))}")
    url = spec["url"]
    for field in ("CLOUDFLARE_ACCOUNT_ID",):
        if "{" + field + "}" in url:
            if not os.environ.get(field):
                raise ValueError(f"provider {name} needs {field} in the environment")
            url = url.replace("{" + field + "}", os.environ[field])
    # A NAMED CLIENT. MEASURED at 2.28.0: Groq, Cerebras and Together all answered 403 to urllib's
    # default `Python-urllib/3.x` — the same refusal from three vendors behind the same bot filter,
    # which is a fact about the client, not about the keys.
    headers = {"Content-Type": "application/json", "User-Agent": "thea-atlas-abtest/1.0"}
    if spec["keys"]:
        key = next((os.environ[k] for k in spec["keys"] if os.environ.get(k)), None)
        if key is None:
            raise ValueError(f"provider {name} needs one of {spec['keys']} in the environment")
        headers["Authorization"] = f"Bearer {key}"
    return url, headers


_PACERS: dict[str, resilience.Pacer] = {}
_BREAKERS: dict[str, resilience.Breaker] = {}


def complete(provider: str, model: str, prompt: str, timeout: int, max_tokens: int = 120) -> tuple[str, int | None]:
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
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()

    def once() -> dict:
        pacer.wait()
        request = urllib.request.Request(url, data=body, headers=headers)  # noqa: S310 — declared endpoints
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.load(response)
    payload = resilience.call(once, attempts=3, base=2.0, cap=30.0, deadline=timeout * 3.0, breaker=breaker)
    if not payload.get("choices"):
        # A 200 CARRYING AN ERROR BODY. openrouter answered `{"error": ...}` with no choices, which
        # surfaced as a bare KeyError 'choices': a refusal with no reason in it.
        raise ValueError(f"{provider} returned no choices: {str(payload.get('error', payload))[:160]}")
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
        done = subprocess.run([*PROVIDERS[provider]["cli"], "--model", model], input=prompt, cwd=cwd,  # noqa: S603
                              capture_output=True, text=True, timeout=timeout, check=False)
    try:
        out = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{provider} printed no JSON (exit {done.returncode}): {done.stderr.strip()[:160]}") from exc
    if out.get("is_error"):
        raise ValueError(f"{provider} refused: {str(out.get('result'))[:160]}")
    u = out.get("usage") or {}
    # Cached input is still input the model read: a repeated long arm hits the cache, and dropping
    # the cached part would credit the ARM with the cache's saving.
    read = int(u.get("input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0))
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
    """`providers.py` lists each provider and whether its key NAME is set — values are never shown."""
    for name, spec in sorted(PROVIDERS.items()):
        ready = not spec["keys"] or any(os.environ.get(k) for k in spec["keys"])
        print(f"  {'ready ' if ready else 'no key'} {name:<11} rpm {spec['rpm']:<4} keys {', '.join(spec['keys']) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
