"""LLM chat client supporting multiple providers (OpenAI, Anthropic & Ollama).

The "dual-AI" aspect: each agent can be wired to a different provider/model,
so the architect could run on Anthropic while the engineer runs on Ollama, or
vice versa.

Environment variables used:

- LLM_PROVIDER            default provider: "openai", "anthropic" or "ollama"
- OPENAI_API_KEY          OpenAI key
- OPENAI_BASE_URL         defaults to https://api.openai.com/v1
- OPENAI_MODEL            defaults to gpt-4o-mini
- ANTHROPIC_API_KEY       Anthropic key
- ANTHROPIC_BASE_URL      defaults to https://api.anthropic.com
- ANTHROPIC_MODEL         defaults to claude-sonnet-4-20250514
- OLLAMA_BASE_URL         defaults to http://localhost:11434/v1
- OLLAMA_MODEL            defaults to qwen2.5:7b
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"


class LLMError(RuntimeError):
    """Raised when the upstream LLM API call fails."""


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    latency_ms: int = 0
    usage: dict = field(default_factory=dict)


class BaseLLMClient:
    """Minimal protocol used by agents: complete(messages) -> str."""

    provider: str = "abstract"
    model: str = ""

    def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResult:
        raise NotImplementedError


class OpenAICompatibleClient(BaseLLMClient):
    """Speaks the OpenAI Chat Completions API (works with Azure/deepseek/local too)."""

    provider = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
        provider_label: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self.timeout = timeout
        if provider_label:
            self.provider = provider_label
        if not self.api_key and not self._is_local():
            raise LLMError("OPENAI_API_KEY is not set (only skipped for local endpoints).")

    def _is_local(self) -> bool:
        host = self.base_url.split("://", 1)[-1].split("/", 1)[0].lower()
        return host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local")

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResult:
        start = time.monotonic()
        payload: dict = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"OpenAI API error {exc.response.status_code}: {exc.response.text[:500]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        choice = data["choices"][0]
        text = choice["message"]["content"] or ""
        return LLMResult(
            text=text,
            model=data.get("model", self.model),
            provider=self.provider,
            latency_ms=int((time.monotonic() - start) * 1000),
            usage=data.get("usage", {}),
        )


class AnthropicClient(BaseLLMClient):
    """Speaks the Anthropic Messages API."""

    provider = "anthropic"

    SYSTEM_ROLE = "system"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set.")
        self.base_url = (base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")).rstrip("/")
        self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_CLAUDE_MODEL)
        self.timeout = timeout

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResult:
        start = time.monotonic()
        system_parts = [m.content for m in messages if m.role == self.SYSTEM_ROLE]
        others = [m for m in messages if m.role != self.SYSTEM_ROLE]
        payload: dict = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in others],
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Anthropic API error {exc.response.status_code}: {exc.response.text[:500]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        text = "".join(b.get("text", "") for b in data.get("content", []))
        return LLMResult(
            text=text,
            model=data.get("model", self.model),
            provider=self.provider,
            latency_ms=int((time.monotonic() - start) * 1000),
            usage=data.get("usage", {}),
        )


def build_client(
    provider: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> BaseLLMClient:
    """Create a client for the given provider ("openai" | "anthropic" | "ollama")."""
    provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
    if provider == "openai":
        return OpenAICompatibleClient(api_key, base_url, model)
    if provider == "anthropic":
        return AnthropicClient(api_key, base_url, model)
    if provider == "ollama":
        return OpenAICompatibleClient(
            api_key="local",  # Ollama needs no key; harmless if echoed nowhere
            base_url=base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            model=model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            provider_label="ollama",
        )
    raise LLMError(f"Unknown provider: {provider!r} (use 'openai', 'anthropic' or 'ollama')")


def json_from_llm(text: str) -> dict:
    """Best-effort parse of JSON from an LLM response (strips fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Could not parse JSON from model output: {exc}") from exc