"""CLI runner so the pipeline can be used without the web server.

Usage:
    python -m src.cli "Build a todo REST API" --architect anthropic --engineer openai
"""

from __future__ import annotations

import argparse
import json
import sys

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
    return 0


if __name__ == "__main__":
    sys.exit(main())