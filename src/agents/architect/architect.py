"""Architect agent: turns a task into a design document."""

from __future__ import annotations

from ..base import BaseAgent
from ...models import Task, DesignDoc

SYSTEM = """\
You are a senior software architect. You produce concise, actionable design \
documents. Always reply with a single JSON object only, no prose around it.

JSON schema:
{
  "summary": string,
  "architecture": string,
  "tech_stack": [string, ...],
  "components": [{"name": string, "responsibility": string,
                  "interfaces": [string, ...], "dependencies": [string, ...]}],
  "data_flow": [string, ...],
  "risks": [string, ...],
  "decisions": [string, ...]
}
"""


class ArchitectAgent(BaseAgent):
    name = "architect"
    system_prompt = SYSTEM

    def run(self, task: Task) -> DesignDoc:
        prompt = (
            f"Task title: {task.title}\n"
            f"Description: {task.description}\n"
            "Requirements:\n"
            + "\n".join(f"- {r}" for r in task.requirements)
            + "\n\nProduce the design document as JSON."
        )
        text = self.prompt(prompt)
        return self.parse_model(DesignDoc, text)