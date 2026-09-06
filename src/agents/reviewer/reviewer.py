"""Reviewer agent: critically reviews the produced code."""

from __future__ import annotations

from ..base import BaseAgent
from ...models import Task, DesignDoc, CodePatch, ReviewReport

SYSTEM = """\
You are a meticulous senior reviewer. You review code for correctness, security, \
design adherence and runnability. Be honest and specific. Always reply with a \
single JSON object only.

JSON schema:
{
  "verdict": "approved" | "needs-changes" | "rejected",
  "score": integer 0-100,
  "issues": [{"severity": "critical"|"major"|"minor"|"nit",
              "file": string, "line": integer|null, "message": string}],
  "suggestions": [string, ...],
  "summary": string
}
"""


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    system_prompt = SYSTEM

    def run(self, task: Task, design: DesignDoc, patch: CodePatch) -> ReviewReport:
        files = "\n\n".join(
            f"--- {fp.path} ---\n{fp.content}" for fp in patch.files
        )
        prompt = (
            f"Task title: {task.title}\n"
            f"Requirements:\n" + "\n".join(f"- {r}" for r in task.requirements)
            + f"\n\nDesign summary: {design.summary}\n"
            f"Engineer overview: {patch.overview}\n"
            f"\nCode:\n{files}\n"
            "\nReview the code for correctness, security, requirement coverage, "
            "and whether it would actually run. Return JSON."
        )
        text = self.prompt(prompt)
        return self.parse_model(ReviewReport, text)