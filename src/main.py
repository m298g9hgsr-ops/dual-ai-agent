"""FastAPI entry point: exposes the dual-AI agent pipeline over HTTP."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import PipelineResult, Task
from .pipeline import AgentTeam

app = FastAPI(
    title="Dual-AI Agent Team",
    version="0.1.0",
    description="Architect -> Engineer -> Reviewer pipeline powered by two AI providers.",
)

_team: AgentTeam | None = None


def get_team() -> AgentTeam:
    global _team
    if _team is None:
        _team = AgentTeam.from_providers()
    return _team


class RunResponse(BaseModel):
    result: PipelineResult
    endpoint: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "team": [agent.describe() for agent in [get_team().architect, get_team().engineer, get_team().reviewer]],
    }


@app.post("/run", response_model=RunResponse)
def run(task: Task) -> RunResponse:
    try:
        result = get_team().run(task)
    except Exception as exc:  # surface upstream errors cleanly
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RunResponse(result=result, endpoint="architect->engineer->reviewer")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)