"""CLI runner so the pipeline can be used without the web server.

Usage:
    python -m src.cli "Build a todo REST API" --architect anthropic --engineer openai
    python -m src.cli "..." --output ./out
"""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
from pathlib import Path

from .models import Task
from .pipeline import AgentTeam, SparTeam
from .utils.llm import build_client


def _parse_client(value: str) -> dict:
    """Parse provider[:model] into kwargs, e.g. anthropic:claude-haiku-4-5."""
    provider, _, model = value.partition(":")
    kw = {"provider": provider}
    if model:
        kw["model"] = model
    return kw


def _safe_path(root: Path, relative: str) -> Path:
    """Return root-joined path, refusing path traversal outside root."""
    rel = posixpath.normpath(relative.replace("\\", "/").strip("/"))
    if rel in {"", ".", ".."} or rel.startswith("../"):
        raise ValueError(f"Refusing unsafe path: {relative!r}")
    if rel.startswith("relative/"):
        rel = rel[len("relative/") :]
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError(f"Refusing unsafe path: {relative!r}")
    return p


def write_output(root: Path, result) -> int:
    """Write generated files + design/review report to disk. Returns # of files."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped: list[str] = []
    for fp in result.patch.files:
        try:
            target = _safe_path(root, fp.path)
        except ValueError as exc:
            skipped.append(str(exc))
            print(f"[warn] skipped: {exc}", file=sys.stderr)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fp.content, encoding="utf-8", newline="\n")
        written += 1

    report = {
        "status": result.status,
        "review_verdict": result.review.verdict,
        "review_score": result.review.score,
        "design": result.design.model_dump(),
        "files": [fp.path for fp in result.patch.files],
        "issues": [i.model_dump() for i in result.review.issues],
        "suggestions": result.review.suggestions,
        "meta": result.meta,
    }
    (root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return written


def spar_main(argv: list[str]) -> int:
    """Red/blue adversarial exercise: RED attacks, BLUE defends, JUDGE scores."""
    p = argparse.ArgumentParser(prog="dual-ai-agent spar")
    p.add_argument("--target", required=True, help="Authorized lab target URL (localhost by default).")
    p.add_argument("--executor", default="local", help="local | wsl[:distro[:user]] | docker:<container>")
    p.add_argument("--rounds", type=int, default=1)
    p.add_argument("--max-steps", type=int, default=5)
    p.add_argument("--objective", action="append", default=[], help="Attack objective (repeatable).")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--output", default=None, help="Write spar.json + report.md here.")
    args = p.parse_args(argv)

    team = SparTeam.from_providers(executor=args.executor, timeout=args.timeout)
    result = team.run(
        args.target,
        objectives=args.objective or None,
        rounds=args.rounds,
        max_steps=args.max_steps,
    )

    print(f"\n=== SPAR · {result.target} ===")
    print(f"步驟 {len(result.plan.steps)} · 執行 {len(result.attack.commands_run)} 條指令")
    print(f"\n[RED] 發現 {len(result.attack.findings)} 個:")
    for f in result.attack.findings:
        print(f"  - [{f.severity.upper()}] {f.title}")
        if f.evidence:
            print(f"      證據: {f.evidence[:120]}")
    print(f"\n[BLUE] 防禦動作 {len(result.defense.actions)} 項:")
    for a in result.defense.actions:
        print(f"  - ({a.priority}) {a.area}: {a.action}")
    print(f"\n[JUDGE] {result.verdict.verdict} — 總分 {result.verdict.score} "
          f"(攻 {result.verdict.attacker_score} / 防 {result.verdict.defender_score})")
    print(f"  {result.verdict.commentary}")

    if args.output:
        root = Path(args.output).resolve()
        root.mkdir(parents=True, exist_ok=True)
        (root / "spar.json").write_text(
            json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        md = [
            f"# SPAR 對抗報告 · {result.target}",
            "",
            f"- 回合數: {result.rounds} · 執行環境: {result.meta.get('executor')}",
            f"- 裁判: **{result.verdict.verdict}** · 總分 {result.verdict.score}"
            f"（攻擊 {result.verdict.attacker_score} / 防禦 {result.verdict.defender_score}）",
            "",
            "## RED — 攻擊發現",
        ]
        for f in result.attack.findings:
            md.append(f"### [{f.severity.upper()}] {f.title}")
            if f.impact:
                md.append(f"- 影響: {f.impact}")
            if f.evidence:
                md.append(f"- 證據:\n\n```\n{f.evidence[:600]}\n```")
        md.append("\n## BLUE — 防禦計畫")
        for a in result.defense.actions:
            md.append(f"- **({a.priority}) {a.area}** — {a.action} {('· 修：' + ', '.join(a.addresses)) if a.addresses else ''}")
        if result.defense.residual_risk:
            md.append("\n### 殘餘風險")
            md += [f"- {r}" for r in result.defense.residual_risk]
        md.append("\n## 執行過的指令")
        md += [f"- `{c}`" for c in result.attack.commands_run]
        (root / "report.md").write_text("\n".join(md), encoding="utf-8")
        print(f"\n[written] {root / 'spar.json'}")
        print(f"[written] {root / 'report.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "spar":
        return spar_main(argv[1:])
    parser = argparse.ArgumentParser(
        prog="dual-ai-agent",
        description="Run the architect -> engineer -> reviewer pipeline.",
    )
    parser.add_argument("task", help="Task description.")
    parser.add_argument("--title", default="CLI task", help="Task title.")
    parser.add_argument(
        "--requirement",
        action="append",
        default=[],
        help="An explicit requirement (repeatable).",
    )
    parser.add_argument(
        "--architect",
        default=None,
        help="Architect client: openai or anthropic[:model]",
    )
    parser.add_argument(
        "--engineer",
        default=None,
        help="Engineer client: openai or anthropic[:model]",
    )
    parser.add_argument(
        "--reviewer",
        default=None,
        help="Reviewer client: openai or anthropic[:model]",
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Print generated file contents.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write generated files + report.json into this directory.",
    )
    args = parser.parse_args(argv)

    def _team() -> AgentTeam:
        if args.architect or args.engineer or args.reviewer:
            return AgentTeam.from_clients(
                architect=build_client(**_parse_client(args.architect)) if args.architect else build_client(),
                engineer=build_client(**_parse_client(args.engineer)) if args.engineer else build_client(),
                reviewer=build_client(**_parse_client(args.reviewer)) if args.reviewer else build_client(),
            )
        return AgentTeam.from_providers()

    task = Task(
        title=args.title,
        description=args.task,
        requirements=args.requirement,
    )

    result = _team().run(task)

    out: dict = {
        "status": result.status,
        "review_verdict": result.review.verdict,
        "review_score": result.review.score,
        "design": result.design.model_dump(),
        "files": [fp.path for fp in result.patch.files],
        "issues": [i.model_dump() for i in result.review.issues],
        "suggestions": result.review.suggestions,
    }
    if args.show_code:
        out["full_patch"] = result.patch.model_dump()

    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.output:
        n = write_output(Path(args.output), result)
        print(f"\n[written] {n} file(s) -> {Path(args.output).resolve()}")
        print("[written] design + review -> report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())