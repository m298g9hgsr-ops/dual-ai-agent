"""Dual-AI agent pipeline: architect -> engineer -> reviewer.

Two AI models can be paired (e.g. OpenAI for architect, Anthropic for
engineer) to get cross-model review. The AgentTeam wires it all together.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .agents.architect import ArchitectAgent
from .agents.attacker import AttackerAgent
from .agents.defender import DefenderAgent
from .agents.engineer import EngineerAgent
from .agents.judge import JudgeAgent
from .agents.reviewer import ReviewerAgent
from .models import DesignDoc, PipelineResult, SparResult, Task
from .tools.executor import CommandExecutor, build_executor
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
                architect_client
                or build_client(
                    architect_provider or os.getenv("ARCHITECT_PROVIDER"),
                    model=os.getenv("ARCHITECT_MODEL"),
                )
            ),
            engineer=EngineerAgent(
                engineer_client
                or build_client(
                    engineer_provider or os.getenv("ENGINEER_PROVIDER"),
                    model=os.getenv("ENGINEER_MODEL"),
                )
            ),
            reviewer=ReviewerAgent(
                reviewer_client
                or build_client(
                    reviewer_provider or os.getenv("REVIEWER_PROVIDER"),
                    model=os.getenv("REVIEWER_MODEL"),
                )
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


@dataclass
class SparTeam:
    """Red/blue adversarial team: RED attacks, BLUE defends, JUDGE scores.

    Each agent can run on a different provider/model, so the attack side and the
    defense side can literally be different models (the "dual-AI" idea applied to
    security exercises).
    """

    attacker: AttackerAgent
    defender: DefenderAgent
    judge: JudgeAgent
    executor: CommandExecutor

    @classmethod
    def from_providers(
        cls,
        *,
        attacker_provider: str | None = None,
        defender_provider: str | None = None,
        judge_provider: str | None = None,
        executor: str = "local",
        timeout: int = 120,
    ) -> "SparTeam":
        return cls(
            attacker=AttackerAgent(
                build_client(
                    attacker_provider or os.getenv("ATTACKER_PROVIDER"),
                    model=os.getenv("ATTACKER_MODEL"),
                )
            ),
            defender=DefenderAgent(
                build_client(
                    defender_provider or os.getenv("DEFENDER_PROVIDER"),
                    model=os.getenv("DEFENDER_MODEL"),
                )
            ),
            judge=JudgeAgent(
                build_client(
                    judge_provider or os.getenv("JUDGE_PROVIDER"),
                    model=os.getenv("JUDGE_MODEL"),
                )
            ),
            executor=build_executor(executor, timeout=timeout),
        )

    def run(
        self,
        target: str,
        objectives: list[str] | None = None,
        rounds: int = 1,
        max_steps: int = 5,
    ) -> SparResult:
        plan = None
        attack = None
        defense = None
        verdict = None
        for _ in range(max(1, rounds)):
            plan = self.attacker.plan(target, objectives, max_steps=max_steps)
            results = [self.executor.run(step.command, target) for step in plan.steps]
            attack = self.attacker.report(plan, results)
            defense = self.defender.defend(attack)
            verdict = self.judge.score(attack, defense)
        assert plan and attack and defense and verdict
        meta = {
            self.attacker.name: self.attacker.describe(),
            self.defender.name: self.defender.describe(),
            self.judge.name: self.judge.describe(),
            "executor": self.executor.label,
            "commands": len(attack.commands_run),
        }
        return SparResult(
            target=target,
            plan=plan,
            attack=attack,
            defense=defense,
            verdict=verdict,
            rounds=max(1, rounds),
            status="ok",
            meta=meta,
        )