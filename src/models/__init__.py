"""Pydantic models for the dual-AI agent pipeline."""

from .models import (
    CodePatch,
    Component,
    DesignDoc,
    FilePatch,
    Issue,
    PipelineResult,
    ReviewReport,
    Task,
)
from .spar import (
    AttackPlan,
    AttackReport,
    AttackStep,
    DefenseAction,
    DefenseReport,
    Finding,
    SparResult,
    SparVerdict,
)

__all__ = [
    "AttackPlan",
    "AttackReport",
    "AttackStep",
    "CodePatch",
    "Component",
    "DefenseAction",
    "DefenseReport",
    "DesignDoc",
    "FilePatch",
    "Finding",
    "Issue",
    "PipelineResult",
    "ReviewReport",
    "SparResult",
    "SparVerdict",
    "Task",
]
