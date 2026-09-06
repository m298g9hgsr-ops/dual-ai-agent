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
from .pipeline import AgentTeam
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


def main(argv: list[str] | None = None) -> int:
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