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

# Ollama (local, no API key needed): write the generated code to ./out/
python -m src.cli "Build a todo REST API with FastAPI and SQLite" \
    --requirement "CRUD endpoints" --output ./out
# -> ./out/<generated files> + ./out/report.json (design + review report)
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
| `ATTACKER_PROVIDER` / `DEFENDER_PROVIDER` / `JUDGE_PROVIDER` | red/blue mode per-agent provider | falls back to `LLM_PROVIDER` |
| `ATTACKER_MODEL` / `DEFENDER_MODEL` / `JUDGE_MODEL` | red/blue mode per-agent model | falls back to `OPENAI_MODEL` |
| `SPAR_ALLOWED_TARGETS` | hosts the attack agent may touch | `127.0.0.1,localhost` |

## Red/blue adversarial mode

Two AI brains on opposite sides of the wall: **RED** attacks an authorized lab
target, **BLUE** turns the findings into a remediation plan, **JUDGE** scores both
sides. RED and BLUE can run on *different* models — that is the dual-AI idea applied
to security work.

```
Target ──▶ RED (plan → run tools → findings) ──▶ BLUE (defense plan) ──▶ JUDGE (score)
```

```bash
# Attack a local lab target through a WSL Kali shell, write the report
python -m src.cli spar --target http://127.0.0.1:3000 --executor wsl --max-steps 4 \
    --output ./out/spar-juice

# Executors: local | wsl[:distro[:user]] | docker:<container>
```

Output: `spar.json` (full structured result) and `report.md` (readable report with
findings, evidence, defense actions and residual risk).

### Safety guardrails (always on)

| Guard | Behaviour |
|---|---|
| Target allowlist | commands run only against hosts in `SPAR_ALLOWED_TARGETS` (default localhost only) |
| Destructive-pattern block | `rm -rf /`, `dd`, `shutdown`, `curl … \| sh`, `DROP DATABASE`, … are refused and logged as skipped |
| Non-destructive scope | the attacker's system prompt forbids exfiltration, persistence and DoS |
| Evidence rule | a finding is only reported when the tool output proves it |

### Containerized red/blue

```bash
docker compose up -d red blue       # attacker + defender containers
docker compose exec red bash -lc "apt-get update && apt-get install -y nmap curl nikto gobuster"
docker compose --profile target up -d target    # optional Juice Shop on :3000
```

The agent code is mounted into both containers, so the same run can be driven from
inside the red container (`--executor docker:dual-ai-red`) or from the host.

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