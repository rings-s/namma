"""Provider-agnostic LLM gateway.

Speaks the OpenAI-compatible Chat Completions contract (``POST /chat/completions``),
which every provider we care about implements: free hosted models for testing
(Groq, OpenRouter, Google Gemini's OpenAI endpoint) and local private models for
production (Ollama, vLLM, llama.cpp). Switching between them changes only three
settings — ``AI_BASE_URL`` / ``AI_API_KEY`` / ``AI_MODEL`` — never this code:

    # Free hosted (testing)
    AI_BASE_URL=https://api.groq.com/openai/v1
    AI_MODEL=llama-3.3-70b-versatile

    # Local & private (Ollama)
    AI_BASE_URL=http://localhost:11434/v1
    AI_API_KEY=ollama
    AI_MODEL=llama3.1

``transport`` is injectable so tests run against ``httpx.MockTransport`` without
network access, mirroring the Taqnyat/Moyasar gateway pattern.
"""

import time
from urllib.parse import urlsplit

import httpx
from django.conf import settings

#: Known OpenAI-compatible hosts mapped to a stable provider slug. Anything
#: unrecognised falls back to its hostname (or "local" for loopback), so
#: provenance is always populated even for self-hosted runtimes.
_PROVIDER_BY_HOST = {
    "api.groq.com": "groq",
    "openrouter.ai": "openrouter",
    "api.openai.com": "openai",
    "generativelanguage.googleapis.com": "google",
    "api.anthropic.com": "anthropic",
}


def _derive_provider(base_url):
    host = (urlsplit(base_url).hostname or "").lower()
    if host in _PROVIDER_BY_HOST:
        return _PROVIDER_BY_HOST[host]
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
        return "local"
    return host or "unknown"


class AIError(Exception):
    """A failed call to the LLM provider.

    ``retryable`` marks transient failures (network errors, HTTP 429/5xx) that a
    Celery task may safely retry; authentication/model errors (4xx) are final.
    """

    def __init__(self, message, status_code=None, payload=None, retryable=False):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
        self.retryable = retryable


class ChatResult:
    """A normalized chat completion: the assistant text plus the provenance a
    caller needs to persist (provider, resolved model, token usage, latency)."""

    def __init__(
        self,
        content,
        prompt_tokens=0,
        completion_tokens=0,
        model="",
        provider="",
        latency_ms=0,
    ):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.model = model
        self.provider = provider
        self.latency_ms = latency_ms


class AIClient:
    """Thin wrapper over an OpenAI-compatible Chat Completions endpoint."""

    def __init__(
        self, api_key=None, base_url=None, model=None, transport=None, timeout=None
    ):
        self.model = model or settings.AI_MODEL
        resolved_base_url = base_url or settings.AI_BASE_URL
        self.provider = _derive_provider(resolved_base_url)
        key = api_key if api_key is not None else settings.AI_API_KEY
        headers = {"Content-Type": "application/json"}
        # Local runtimes (Ollama) accept any/no key; hosted providers require one.
        if key:
            headers["Authorization"] = f"Bearer {key}"
        resolved_timeout = (
            timeout
            if timeout is not None
            else getattr(settings, "AI_REQUEST_TIMEOUT", 60.0)
        )
        self._client = httpx.Client(
            base_url=resolved_base_url.rstrip("/"),
            headers=headers,
            timeout=resolved_timeout,
            transport=transport,
        )

    def chat(
        self,
        messages,
        *,
        model=None,
        temperature=0.3,
        max_tokens=1024,
        response_format=None,
    ):
        """Run one chat completion. ``messages`` is the OpenAI role/content list.

        ``response_format`` (e.g. ``{"type": "json_object"}``) is forwarded only
        when given — many local runtimes ignore it, so callers that need JSON
        prompt for it explicitly and parse defensively rather than relying on it.
        """
        body = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            body["response_format"] = response_format

        started = time.perf_counter()
        try:
            response = self._client.post("/chat/completions", json=body)
        except httpx.HTTPError as exc:
            raise AIError(f"AI request failed: {exc}", retryable=True) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if not response.is_success:
            error = payload.get("error")
            message = error.get("message") if isinstance(error, dict) else error
            raise AIError(
                message or f"AI provider returned HTTP {response.status_code}",
                status_code=response.status_code,
                payload=payload,
                retryable=response.status_code == 429 or response.status_code >= 500,
            )

        choices = payload.get("choices") or []
        if not choices:
            raise AIError("AI provider returned no choices.", payload=payload)
        content = (choices[0].get("message") or {}).get("content") or ""
        usage = payload.get("usage") or {}
        return ChatResult(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            model=payload.get("model") or self.model,
            provider=self.provider,
            latency_ms=latency_ms,
        )

    def close(self):
        self._client.close()
