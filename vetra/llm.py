"""
Language-model access. Nothing outside this file knows which vendor is in use.

Any OpenAI-compatible service works by setting three things in .env:

    LLM_BASE_URL=https://api.example.com/v1
    LLM_API_KEY=...
    LLM_MODEL_PLAN=model-a,model-b       # tried in order when one is rate-limited
    LLM_MODEL_COMPOSE=model-c,model-d

With none of them set it uses Groq and GROQ_API_KEY, as rag/ does.

A vendor that isn't OpenAI-compatible needs one class with this file's complete() method.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

GROQ_URL = "https://api.groq.com/openai/v1"
DEFAULT_ROLES = {
    "plan": ("openai/gpt-oss-20b", "qwen/qwen3.8-27b"),
    "compose": ("openai/gpt-oss-120b", "openai/gpt-oss-20b"),
}
REST_SECONDS = 600  # a model at its limit isn't tried again for this long
BUSY_SECONDS = 15   # a model that says it's overloaded is worth trying again soon
MAX_CALLS = 6       # for one question: the limit the proposal holds to
MAX_WAIT = 20       # a citizen will wait this long for a per-minute limit to pass


class LLMError(RuntimeError):
    """The call failed and retrying the same request won't help."""


class RateLimited(LLMError):
    """This model is at its limit; another model may not be."""

    def __init__(self, model: str, retry_after: float = 0):
        super().__init__(model)
        self.retry_after = retry_after


class RequestTooLarge(LLMError):
    """Too much text for this model; send less."""


class BadOutput(LLMError):
    """The model's reply failed the vendor's own format check; asking again may work."""


class BudgetExceeded(LLMError):
    """This question has used all its LLM calls."""


@dataclass
class Reply:
    text: str
    model: str
    tokens: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_cached: int = 0    # part of tokens_in, billed lower
    tokens_thinking: int = 0  # part of tokens_out, hidden from the reply but billed


class Provider(Protocol):
    def complete(self, model: str, messages: list[dict], json_mode: bool = False) -> Reply: ...


class OpenAICompatible:
    def __init__(self, base_url: str, key: str, timeout: float = 90, reasoning: dict[str, str] | None = None):
        self.base_url, self.key, self.timeout = base_url.rstrip("/"), key, timeout
        self.reasoning = reasoning or {}   # model: effort. Hidden thinking is billed as output

    def complete(self, model: str, messages: list[dict], json_mode: bool = False) -> Reply:
        import requests

        body: dict = {"model": model, "messages": messages, "temperature": 0.1}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if model in self.reasoning:
            body["reasoning_effort"] = self.reasoning[model]
        try:
            r = requests.post(f"{self.base_url}/chat/completions", json=body, timeout=self.timeout,
                              headers={"Authorization": f"Bearer {self.key}"})
        except (requests.Timeout, requests.ConnectionError) as exc:  # the next model may well answer
            raise RateLimited(model, BUSY_SECONDS) from exc
        except requests.RequestException as exc:
            raise LLMError(f"{model}: {type(exc).__name__}") from exc
        if r.status_code == 429:
            wait = r.headers.get("retry-after", "")
            raise RateLimited(model, float(wait) if wait.replace(".", "", 1).isdigit() else 0)
        if r.status_code == 503:  # overloaded, which passes quickly
            raise RateLimited(model, BUSY_SECONDS)
        if r.status_code == 404:  # retired or not offered to this account, so the next model should run
            raise RateLimited(model)
        if r.status_code == 413:
            raise RequestTooLarge(model)
        if r.status_code == 400 and "json_validate_failed" in r.text:
            raise BadOutput(model)
        if not r.ok:
            raise LLMError(f"{model}: HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        # Some models put their reasoning in the reply, between these tags.
        text = re.sub(r"<think>.*?(?:</think>|$)", "", data["choices"][0]["message"].get("content") or "", flags=re.S).strip()
        usage = data.get("usage") or {}
        return Reply(text, model, usage.get("total_tokens", 0), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                     (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                     (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0))


def from_env() -> "Models":
    """The configured models. Reads .env at the project root."""
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not key:
        raise LLMError("No API key: set LLM_API_KEY (or GROQ_API_KEY) in .env")
    roles = dict(DEFAULT_ROLES)
    for role in roles:
        chosen = os.environ.get(f"LLM_MODEL_{role.upper()}")
        if chosen:
            roles[role] = tuple(m.strip() for m in chosen.split(",") if m.strip())
    reasoning = dict(p.strip().split(":", 1) for p in (os.environ.get("LLM_REASONING") or "").split(",") if ":" in p)
    return Models(OpenAICompatible(os.environ.get("LLM_BASE_URL") or GROQ_URL, key, reasoning=reasoning), roles)


@dataclass
class Models:
    """Which models do which job, and which of them are resting after a rate limit."""
    provider: Provider
    roles: dict[str, tuple[str, ...]]
    resting: dict[str, float] = field(default_factory=dict)

    def call(self, role: str, messages: list[dict], meter: "Meter", json_mode: bool = False,
             waited: bool = False) -> Reply:
        models = self.roles[role]
        ready = [m for m in models if self.resting.get(m, 0) <= time.time()] or list(models)
        last: LLMError | None = None
        for model in ready:
            meter.spend()
            try:
                reply = self.provider.complete(model, messages, json_mode)
            except RateLimited as exc:
                # A per-minute limit passes soon; a daily one is worth skipping for a while.
                self.resting[model] = time.time() + (exc.retry_after or REST_SECONDS)
                meter.calls -= 1   # nothing was spent, so a busy provider shouldn't use up the budget
                last = exc
                continue
            except BadOutput as exc:
                last = exc
                if json_mode:  # the reply is parsed anyway; only the vendor's own check failed
                    return self.call(role, messages, meter, json_mode=False)
                continue
            meter.record(role, reply)
            return reply
        if isinstance(last, RateLimited) and not waited and 0 < last.retry_after <= MAX_WAIT:
            time.sleep(last.retry_after)
            return self.call(role, messages, meter, json_mode, waited=True)
        raise last or LLMError(f"no model for {role}")


@dataclass
class Meter:
    """LLM calls and tokens for one question. Refuses to go over the limit."""
    limit: int = MAX_CALLS
    calls: int = 0
    tokens: int = 0
    steps: list[dict] = field(default_factory=list)

    def spend(self) -> None:
        if self.calls >= self.limit:
            raise BudgetExceeded(f"{self.limit} LLM calls used")
        self.calls += 1

    def record(self, role: str, reply: Reply) -> None:
        self.tokens += reply.tokens
        self.steps.append({"role": role, "model": reply.model, "tokens": reply.tokens, "in": reply.tokens_in, "out": reply.tokens_out,
                           "cached": reply.tokens_cached, "thinking": reply.tokens_thinking})
