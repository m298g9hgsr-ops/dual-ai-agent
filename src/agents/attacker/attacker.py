"""RED agent: plans and runs an authorized attack against a target."""

from __future__ import annotations

import json

from ..base import BaseAgent
from ...models.spar import AttackPlan, AttackReport
from ...tools.executor import CommandResult

SYSTEM = """\
You are RED, an offensive-security agent working inside an explicitly authorized \
lab (the target is the user's own practice target). You plan small, safe, \
non-destructive reconnaissance steps, then turn raw tool output into evidence-backed \
findings.

Rules:
- Only passive or read-only checks plus harmless proof-of-concept requests.
- Never propose data exfiltration, destructive payloads, persistence, or DoS.
- Every finding must quote the exact output that proves it.
- Reply with a single JSON object only, no prose around it.

JSON schema for the PLAN:
{
  "target": string,
  "objectives": [string, ...],
  "steps": [{"tool": string, "command": string, "purpose": string}, ...],
  "notes": string
}

JSON schema for the REPORT:
{
  "target": string,
  "summary": string,
  "findings": [{"title": string, "severity": "critical|high|medium|low|info",
                 "target": string, "evidence": string, "impact": string}, ...],
  "commands_run": [string, ...]
}
"""


class AttackerAgent(BaseAgent):
    name = "attacker"
    system_prompt = SYSTEM

    def plan(self, target: str, objectives: list[str] | None = None, max_steps: int = 5) -> AttackPlan:
        obj = objectives or [
            "identify exposed services and technologies",
            "check for common misconfigurations and information disclosure",
            "verify input-handling weaknesses with harmless proof-of-concept requests",
        ]
        prompt = (
            f"Target: {target}\n"
            "Objectives:\n" + "\n".join(f"- {o}" for o in obj) + "\n"
            f"Produce at most {max_steps} safe, read-only steps. "
            "Commands run in a Kali-like shell with nmap/curl/nikto/gobuster available. "
            "Target host must stay the same. Return the plan JSON."
        )
        text = self.prompt(prompt, temperature=0.3)
        plan = self.parse_with_retry(AttackPlan, text)
        plan.target = target
        plan.steps = plan.steps[:max_steps]
        return plan

    def report(self, plan: AttackPlan, results: list[CommandResult]) -> AttackReport:
        blocks = []
        for r in results:
            head = f"$ {r.command}"
            if r.skipped:
                head += f"  [SKIPPED: {r.reason}]"
            elif r.returncode != 0:
                head += f"  [exit {r.returncode}]"
            blocks.append(head + "\n" + (r.text()[:2500] or "(no output)"))
        prompt = (
            f"Target: {plan.target}\n"
            "Objectives:\n" + "\n".join(f"- {o}" for o in plan.objectives) + "\n"
            "Raw tool output:\n\n" + "\n\n".join(blocks)[:18000] + "\n\n"
            "List only findings the output actually proves. Quote the proving output in "
            "'evidence'. If nothing is proven, return an empty findings list. Return the report JSON."
        )
        text = self.prompt(prompt, temperature=0.2)
        report = self.parse_with_retry(AttackReport, text)
        report.target = plan.target
        report.commands_run = [r.command for r in results]
        return report
