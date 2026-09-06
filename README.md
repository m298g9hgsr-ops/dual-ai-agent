# Dual-AI Agent Team

A production-oriented AI agent pipeline where three specialist agents — **Architect**,
**Engineer**, and **Reviewer** — collaborate to turn a task into designed, implemented,
and reviewed code. "Dual-AI" means each agent can run on a *different* model/provider
(e.g. Architect on OpenAI, Engineer on Anthropic), giving cross-model design & review.

```
Task ──▶ Architect ──▶ DesignDoc ──▶ Engineer ──▶ CodePatch ──▶ Reviewer ──▶ ReviewReport
```

## Features

- 3 collaborating agents, each a Pydantic-typed stage
- Two LLM providers built in: **OpenAI** (Chat Completions) and **Anthropic** (Messages)
- Per-agent provider, model and base URL override (`.env` or CLI flags)
- REST API (FastAPI) + CLI runner
- Robust JSON parsing (fence stripping, slice-to-object, retry via re-ask)

## Quick start

Python 3.12+ recommended.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then fill in API keys
```

### CLI

```bash
# Same provider for all agents
python -m src.cli "Build a todo REST API with FastAPI and SQLite" \
    --requirement "CRUD endpoints" \
    --requirement "Persistence via SQLite"

# Dual-AI pairing: Architect + Reviewer on Anthropic, Engineer on OpenAI
python -m src.cli "..." --architect anthropic --engineer openai --reviewer anthropic --show-code
```

### Web API

```bash
uvicorn src.main:app --reload --port 8000
```

- `GET /health` — shows which model each agent uses
- `POST /run` — body:

```json
{
  "title": "Todo API",
  "description": "Build a todo REST API.",
  "requirements": ["CRUD endpoints", "SQLite persistence"]
}
```

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | default provider | `openai` |
| `OPENAI_API_KEY` | OpenAI key | — |
| `OPENAI_MODEL` | OpenAI model | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | OpenAI-compatible base | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic key | — |
| `ANTHROPIC_MODEL` | Anthropic model | `claude-sonnet-4-20250514` |
| `ANTHROPIC_BASE_URL` | Anthropic base | `https://api.anthropic.com` |
| `ARCHITECT_PROVIDER` / `ENGINEER_PROVIDER` / `REVIEWER_PROVIDER` | per-agent provider | falls back to `LLM_PROVIDER` |

## Project layout

```
src/
├── main.py          FastAPI app
├── cli.py           CLI runner
├── pipeline.py      AgentTeam orchestrator
├── models/          Pydantic schemas (Task/DesignDoc/CodePatch/ReviewReport)
├── agents/
│   ├── base.py      BaseAgent (prompt + typed parse)
│   ├── architect/   Task -> DesignDoc
│   ├── engineer/    (Task, DesignDoc) -> CodePatch
│   └── reviewer/    (Task, DesignDoc, CodePatch) -> ReviewReport
└── utils/
    └── llm.py       OpenAI & Anthropic clients, JSON extraction
```