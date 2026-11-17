"""JUDGE agent: scores the round (attacker vs defender) and grades the defense."""

from __future__ import annotations

from ..base import BaseAgent
from ...models.spar import AttackReport, DefenseReport, SparVerdict

SYSTEM = """\
You are the JUDGE of a red/blue security exercise. You score both sides:
how good the attack was (did it find real, evidenced issues?) and how good the \
defense was (did it actually address them, with correct priorities?).

Reply with a single JSON object only.

JSON schema:
{
  "verdict": "strong-defense|partial|weak",
  "score": integer 0-100 (overall exercise quality),
  "attacker_score": integer 0-100,
  "defender_score": integer 0-100,
  "confirmed_findings": [string, ...],
  "missed_findings": [string, ...],
  "commentary": string
}
"""


class JudgeAgent(BaseAgent):
    name = "judge"
    system_prompt = SYSTEM

    def score(self, attack: AttackReport, defense: DefenseReport) -> SparVerdict:
        findings = "\n".join(f"- [{f.severity}] {f.title} | evidence: {f.evidence[:120]}" for f in attack.findings)
        actions = "\n".join(f"- ({a.priority}) {a.area}: {a.action} -> fixes {a.addresses}" for a in defense.actions)
        prompt = (
            f"Target: {attack.target}\n"
            f"ATTACK findings:\n{findings or '(none)'}\n\n"
            f"DEFENSE actions:\n{actions or '(none)'}\n\n"
            "Score both sides and give the verdict JSON."
        )
        text = self.prompt(prompt, temperature=0.2)
        return self.parse_with_retry(SparVerdict, text)
