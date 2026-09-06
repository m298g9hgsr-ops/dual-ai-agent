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

    def describe(self) -> dict[str, str]:
        return {
            "name": self.name,
            "provider": self.client.provider,
            "model": self.client.model,
        }