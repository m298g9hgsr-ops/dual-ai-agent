"""Base class shared by all agents in the pipeline."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from ..utils.llm import BaseLLMClient, LLMMessage

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """Agents wrap an LLM client and convert free-form text into typed models."""

    name: str = "agent"
    system_prompt: str = ""

    def __init__(self, client: BaseLLMClient) -> None:
        self.client = client

    def run(self, input: Any) -> Any:
        raise NotImplementedError

    def prompt(self, user_content: str, *, temperature: float = 0.2) -> str:
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        messages.append(LLMMessage(role="user", content=user_content))
        result = self.client.complete(messages, temperature=temperature)
        return result.text

    @staticmethod
    def parse_model(model_cls: type[T], text: str, *, fallback: T | None = None) -> T:
        from ..utils.llm import LLMError, json_from_llm

        try:
            data = json_from_llm(text)
            return model_cls.model_validate(data)
        except (LLMError, ValueError) as exc:
            if fallback is not None:
                return fallback
            raise ValueError(f"{model_cls.__name__} parse failed: {exc}") from exc

    def parse_with_retry(
        self,
        model_cls: type[T],
        text: str,
        *,
        attempts: int = 2,
        hint: str = "Reply with a single valid JSON object and nothing else.",
    ) -> T:
        """Parse typed output; on failure, re-ask the model with a stricter hint."""
        last_exc: Exception | None = None
        current = text
        for attempt in range(max(1, attempts)):
            try:
                return self.parse_model(model_cls, current)
            except Exception as exc:  # noqa: BLE001 - re-ask on any parse problem
                last_exc = exc
                if attempt == max(1, attempts) - 1:
                    break
                current = self.prompt(
                    f"{hint}\n\nYour previous output was:\n{current[:3000]}",
                    temperature=0.0,
                )
        raise ValueError(f"{model_cls.__name__} parse failed after retries: {last_exc}")

    def describe(self) -> dict[str, str]:
        return {
            "name": self.name,
            "provider": self.client.provider,
            "model": self.client.model,
        }