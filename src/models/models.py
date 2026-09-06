"""Pydantic models shared across the dual-AI agent pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Task(BaseModel):
    """A software task to be executed by the agent team."""

    title: str = Field(description="Short task title.")
    description: str = Field(description="Full task description / user story.")
    requirements: list[str] = Field(
        default_factory=list,
        description="Explicit, testable requirements.",
    )


class Component(BaseModel):
    """A single architectural component."""

    name: str
    responsibility: str = Field(description="What this component is responsible for.")
    interfaces: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class DesignDoc(BaseModel):
    """Output of the Architect agent."""

    summary: str
    architecture: str = Field(
        description="High level architecture description (pattern, layering, etc)."
    )
    tech_stack: list[str] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    data_flow: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(
        default_factory=list,
        description="Key design decisions and rationale.",
    )


class FilePatch(BaseModel):
    """A single file produced by the Engineer agent."""

    path: str = Field(description="Relative file path, e.g. src/foo.py.")
    content: str = Field(description="Full file content.")


class CodePatch(BaseModel):
    """Output of the Engineer agent."""

    overview: str
    files: list[FilePatch]
    run_instructions: list[str] = Field(
        default_factory=list,
        description="How to run / verify the produced code.",
    )


class Issue(BaseModel):
    """A single review finding."""

    severity: str = Field(
        description="One of: critical, major, minor, nit.",
    )
    file: str = ""
    line: int | None = None
    message: str


class ReviewReport(BaseModel):
    """Output of the Reviewer agent."""

    verdict: str = Field(description="One of: approved, needs-changes, rejected.")
    score: int = Field(
        ge=0,
        le=100,
        description="Overall quality score 0-100.",
    )
    issues: list[Issue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str


class PipelineResult(BaseModel):
    """Aggregated result of a full architect -> engineer -> reviewer run."""

    task: Task
    design: DesignDoc
    patch: CodePatch
    review: ReviewReport
    status: str = Field(
        description="One of: ok, needs-revision (reviewer wants changes)."
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-agent metadata (provider, model, latency).",
    )