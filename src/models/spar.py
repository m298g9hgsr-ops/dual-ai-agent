"""Models for the RED/BLUE adversarial pipeline (red-blue dual-ai mode)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AttackStep(BaseModel):
    tool: str = Field(description="Tool to use, e.g. nmap, curl, nikto, sqlmap")
    command: str = Field(description="Exact shell command to execute")
    purpose: str = Field(description="What this step verifies")


class AttackPlan(BaseModel):
    target: str
    objectives: list[str] = Field(default_factory=list)
    steps: list[AttackStep] = Field(default_factory=list)
    notes: str = ""


class Finding(BaseModel):
    title: str
    severity: str = Field(description="One of: critical, high, medium, low, info")
    target: str = ""
    evidence: str = Field(default="", description="Verbatim command output proving the finding")
    impact: str = ""


class AttackReport(BaseModel):
    target: str
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)


class DefenseAction(BaseModel):
    area: str = Field(description="e.g. auth, input-validation, network, secrets")
    action: str = Field(description="Concrete remediation step")
    priority: str = Field(description="p0 immediate, p1 soon, p2 later")
    details: str = ""
    addresses: list[str] = Field(default_factory=list, description="Finding titles this action fixes")


class DefenseReport(BaseModel):
    target: str
    summary: str = ""
    actions: list[DefenseAction] = Field(default_factory=list)
    residual_risk: list[str] = Field(default_factory=list)
    quick_wins: list[str] = Field(default_factory=list)


class SparVerdict(BaseModel):
    verdict: str = Field(description="One of: strong-defense, partial, weak")
    score: int = Field(ge=0, le=100)
    attacker_score: int = Field(ge=0, le=100)
    defender_score: int = Field(ge=0, le=100)
    confirmed_findings: list[str] = Field(default_factory=list)
    missed_findings: list[str] = Field(default_factory=list)
    commentary: str = ""


class SparResult(BaseModel):
    target: str
    plan: AttackPlan
    attack: AttackReport
    defense: DefenseReport
    verdict: SparVerdict
    rounds: int = 1
    status: str = Field(default="ok", description="ok | incomplete")
    meta: dict[str, Any] = Field(default_factory=dict)
