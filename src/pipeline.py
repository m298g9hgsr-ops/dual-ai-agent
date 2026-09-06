"""Dual-AI agent pipeline: architect -> engineer -> reviewer.

Two AI models can be paired (e.g. OpenAI for architect, Anthropic for
engineer) to get cross-model review. The AgentTeam wires it all together.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .agents.architect import ArchitectAgent
from .agents.engineer import EngineerAgent
from .agents.reviewer import ReviewerAgent
from .models import DesignDoc, PipelineResult, Task
from .utils.llm import BaseLLMClient, build_client


@dataclass
class AgentTeam:
    """A configured team of the three agents."""

    architect: ArchitectAgent
    engineer: EngineerAgent
    reviewer: ReviewerAgent

    @classmethod
    def from_providers(
        cls,
        *,
        architect_provider: str | None = None,
        engineer_provider: str | None = None,
        reviewer_provider: str | None = None,
        architect_client: BaseLLMClient | None = None,
        engineer_client: BaseLLMClient | None = None,
        reviewer_client: BaseLLMClient | None = None,
    ) -> "AgentTeam":
        return cls(
            architect=ArchitectAgent(
                architect_client or build_client(architect_provider or os.getenv("ARCHITECT_PROVIDER"))
            ),
            engineer=EngineerAgent(
                engineer_client or build_client(engineer_provider or os.getenv("ENGINEER_PROVIDER"))
            ),
            reviewer=ReviewerAgent(
                reviewer_client or build_client(reviewer_provider or os.getenv("REVIEWER_PROVIDER"))
            ),
        )

    @classmethod
    def from_clients(
        cls,
        architect: BaseLLMClient,
        engineer: BaseLLMClient,
        reviewer: BaseLLMClient,
    ) -> "AgentTeam":
        return cls(
            architect=ArchitectAgent(architect),
            engineer=EngineerAgent(engineer),
            reviewer=ReviewerAgent(reviewer),
        )

    def run(self, task: Task) -> PipelineResult:
        design = self.architect.run(task)
        patch = self.engineer.run(task, design)
        review = self.reviewer.run(task, design, patch)

        status = "ok" if review.verdict == "approved" else "needs-revision"
        meta = {
            agent.name: agent.describe()
            for agent in (self.architect, self.engineer, self.reviewer)
        }
        return PipelineResult(
            task=task,
            design=design,
            patch=patch,
            review=review,
            status=status,
            meta=meta,
        )