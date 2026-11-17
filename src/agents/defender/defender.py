"""BLUE agent: turns attacker findings into a concrete defense plan."""

from __future__ import annotations

from ..base import BaseAgent
from ...models.spar import AttackReport, DefenseReport

SYSTEM = """\
You are BLUE, a defensive-security engineer. You receive an attacker's findings \
against an authorized lab target and produce a prioritized remediation plan that a \
small team can actually execute.

Rules:
- One concrete action per entry: what to change, where, and why.
- Priority: p0 = stop the bleeding now, p1 = this sprint, p2 = later.
- Map each action to the finding title(s) it fixes.
- Include residual risk that stays even after the actions land.
- Reply with a single JSON object only, no prose around it.

JSON schema:
{
  "target": string,
  "summary": string,
  "actions": [{"area": string, "action": string, "priority": "p0|p1|p2",
               "details": string, "addresses": [string, ...]}, ...],
  "residual_risk": [string, ...],
  "quick_wins": [string, ...]
}
"""


class DefenderAgent(BaseAgent):
    name = "defender"
    system_prompt = SYSTEM

    def defend(self, attack: AttackReport) -> DefenseReport:
        findings = "\n".join(
            f"- [{f.severity.upper()}] {f.title} (evidence: {f.evidence[:160]}) impact: {f.impact[:160]}"
            for f in attack.findings
        ) or "(attacker reported no findings)"
        prompt = (
            f"Target: {attack.target}\n"
            f"Attacker summary: {attack.summary}\n"
            f"Findings:\n{findings}\n\n"
            "Produce the defense plan JSON."
        )
        text = self.prompt(prompt, temperature=0.3)
        report = self.parse_with_retry(DefenseReport, text)
        report.target = attack.target
        return report
