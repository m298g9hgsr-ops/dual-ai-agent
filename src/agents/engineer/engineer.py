"""Engineer agent: turns a task + design into concrete code."""

from __future__ import annotations

from ..base import BaseAgent
from ...models import Task, DesignDoc, CodePatch

SYSTEM = """\
You are a senior software engineer. You implement features described by a task \
and a design document. Your output must be complete, runnable code — never \
placeholders or "…". Always reply with a single JSON object only.

JSON schema:
{
  "overview": string,
  "files": [{"path": "./relative/path.py", "content": "full file text"}],
  "run_instructions": [string, ...]
}
"""


class EngineerAgent(BaseAgent):
    name = "engineer"
    system_prompt = SYSTEM

    def run(self, task: Task, design: DesignDoc) -> CodePatch:
        components = "\n".join(
            f"- {c.name}: {c.responsibility} (deps: {', '.join(c.dependencies) or 'none'})"
            for c in design.components
        )
        prompt = (
            f"Task title: {task.title}\n"
            f"Description: {task.description}\n"
            f"Requirements:\n" + "\n".join(f"- {r}" for r in task.requirements)
            + f"\n\nDesign summary: {design.summary}\n"
            f"Architecture: {design.architecture}\n"
            f"Tech stack: {', '.join(design.tech_stack)}\n"
            f"Components:\n{components}\n"
            + "\n".join(f"- {r}" for r in design.risks)
            + "\n\nImplement the full codebase as JSON using the declared tech stack."
        )
        text = self.prompt(prompt, temperature=0.1)
        return self.parse_model(CodePatch, text)