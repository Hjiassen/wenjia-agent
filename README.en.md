<div align="center">

<img src="docs/assets/wenjia-mark.svg" alt="wenjia-agent" width="96" height="96" />

# wenjia-agent

Open-source Chinese metaphysics Agents powered by the OpenAI Agents SDK.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![CI](https://github.com/Hjiassen/wenjia-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Hjiassen/wenjia-agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![OpenAI Agents SDK](https://img.shields.io/badge/OpenAI-Agents%20SDK-111111.svg)](https://github.com/openai/openai-agents-python)

[简体中文](README.md) | [English](README.en.md)

[Live Demo](https://www.jiajiahome.top/) | [Deployment Guide](docs/DEPLOYMENT.md) | [Web App](apps/web/README.en.md)

</div>

## Overview

The name `wenjia` means “问甲”. `wenjia-agent` is an open-source Agent project
for Chinese metaphysics scenarios.
It combines deterministic BaZi calculation, OpenAI Agents SDK orchestration,
function tools, session memory, structured reports, and prompt templates into a
lightweight Python project.

The core idea is simple: deterministic metaphysics data is calculated by local
tools, while Agents focus on clarification, routing, explanation, and structured
report generation.

## Contents

- [Live Demo](#live-demo)
- [Who This Is For](#who-this-is-for)
- [Web App Preview](#web-app-preview)
- [Features](#features)
- [Agent Topology](#agent-topology)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Python Usage](#python-usage)
- [Project Layout](#project-layout)
- [Development](#development)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Responsible Use](#responsible-use)

## Live Demo

Try the hosted web app:

https://www.jiajiahome.top/

The demo showcases browser chat, the profile panel, long-term memory, and Agent
flow visualization. Public deployers should add their own authentication, rate
limits, log retention policy, and cost controls.

## Who This Is For

- Developers learning OpenAI Agents SDK multi-agent orchestration, handoffs,
  function tools, and structured outputs.
- Agent app builders who want to separate deterministic domain logic from LLM
  dialogue and explanation.
- Engineers looking for a FastAPI + React + SSE streaming chat reference with
  flow visualization, PWA behavior, and deployment scripts.
- People building open-source prompts, tools, or product prototypes around
  Chinese metaphysics culture.

## Web App Preview

![wenjia-agent Web App preview](docs/assets/web-app-preview.png)

## Features

| Feature | Description |
| --- | --- |
| Multi-agent workflow | A main routing Agent delegates work to specialized Agents. |
| Birth info gate | Personalized metaphysics requests must provide a complete birth profile before analysis. |
| Deterministic BaZi core | BaZi pillars, true solar time, five elements, ten gods, NaYin, ShenSha, KongWang, and life-palace fields are calculated locally. |
| Tool-first reasoning | Agents retrieve chart data through function tools instead of inferring key metaphysics fields directly. |
| Structured outputs | Fortune, relationship, and naming reports are constrained by Pydantic schemas. |
| Prompt-as-code | Long prompts live in `wenjia_agent/prompts` for versioned maintenance and community collaboration. |
| Session memory | Agent conversation memory is backed by `SQLAlchemySession`. |
| Poetry workflow | CLI examples, tests, linting, and development docs are included. |

## Agent Topology

| Agent | Responsibility |
| --- | --- |
| `WenjiaMainAgent` | Routes user intent and hands off work to specialist Agents. |
| `ProfileAgent` | Collects birth profile data, looks up cities, and creates basic BaZi charts. |
| `FortuneAgent` | Generates fortune, career, wealth, relationship, and action-oriented analysis. |
| `RelationshipAgent` | Analyzes compatibility, relationship patterns, and communication suggestions. |
| `NamingAgent` | Generates Chinese naming strategies and name suggestions. |
| `MysticToolsAgent` | Explains tool fields, checks supported locations, and troubleshoots parameters. |

```text
WenjiaMainAgent
  ├─ ProfileAgent
  ├─ FortuneAgent
  ├─ RelationshipAgent
  ├─ NamingAgent
  └─ MysticToolsAgent
```

## Quick Start

### Requirements

- Python 3.11+
- Poetry 1.8+
- Node.js 20+ for the Web frontend
- Docker / Docker Compose for optional containerized runs

### Install

Windows PowerShell:

```powershell
git clone https://github.com/Hjiassen/wenjia-agent.git
cd wenjia-agent
poetry install --with dev
Copy-Item .env.example .env
```

Linux:

```bash
git clone https://github.com/Hjiassen/wenjia-agent.git
cd wenjia-agent
poetry install --with dev
cp .env.example .env
```

### Run the deterministic BaZi demo

This demo calls the local deterministic BaZi core and does not require an API
key.

Windows PowerShell:

```powershell
poetry run python examples\cli_bazi.py
```

Linux:

```bash
poetry run python examples/cli_bazi.py
```

Example output:

```text
四柱八字：
乙亥 辛巳 癸卯 丁巳
五行分布： {'木': 3, '火': 6, '土': 1, '金': 3, '水': 3}
```

### Run the Agent CLI

Fill `OPENAI_API_KEY` in `.env` first.

Windows PowerShell:

```powershell
poetry run python examples\cli_agent.py
```

Linux:

```bash
poetry run python examples/cli_agent.py
```

### Run the Web app

The Web app is a fully separated front/back stack: an **API-only FastAPI
backend** plus a standalone **React + TypeScript (Vite) SPA** built with
[Ant Design X](https://x.ant.design/) (Bubble / Sender / Conversations /
ThoughtChain). Run the two processes side by side.

Backend (fill `OPENAI_API_KEY` in `.env` first):

```bash
poetry run uvicorn apps.web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend (dev server on port 5173, proxies `/api` and `/health` to the backend):

```bash
cd apps/web/frontend
npm install
npm run dev
```

Open http://localhost:5173. For production, `npm run build` emits a static SPA in
`apps/web/frontend/dist/` to host anywhere; allow its origin via
`WENJIA_CORS_ORIGINS`. See [apps/web/README.en.md](apps/web/README.en.md).

Live demo: https://www.jiajiahome.top/

## Configuration

Create `.env` from `.env.example` and configure the runtime values:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
OPENAI_FALLBACK_MODEL=
WENJIA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://www.jiajiahome.top
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
WENJIA_SESSION_HISTORY_LIMIT=40
WENJIA_HARNESS_MAX_TURNS=16
WENJIA_HARNESS_MAX_REVISIONS=1
WENJIA_HARNESS_REVISE=true
WENJIA_INPUT_GUARDRAILS_ENABLED=true
WENJIA_INPUT_MAX_CHARS=8000
WENJIA_LONG_TERM_MEMORY_ENABLED=true
WENJIA_LONG_TERM_MEMORY_MAX_ITEMS=8
WENJIA_MODEL_TIMEOUT_SECONDS=90
WENJIA_TRACE_ENABLED=true
WENJIA_TRACE_DIR=logs/traces
WENJIA_OPENAI_SDK_TRACING=false
```

- `OPENAI_AGENT_MODEL`: lightweight routing, profile collection, and tool-query Agents.
- `OPENAI_ANALYSIS_MODEL`: specialist analysis Agents for fortune, relationship, naming, and follow-up suggestions.
- `OPENAI_FALLBACK_MODEL`: optional backup model used when the primary model times out or errors.
- `WENJIA_CORS_ORIGINS`: browser origins allowed to call the backend; restrict this to real deployment domains.
- `WENJIA_SESSION_HISTORY_LIMIT`: maximum recent session items retrieved for each turn.
- `WENJIA_HARNESS_*`: controls maximum harness turns, revision count, and whether revision is enabled.
- `WENJIA_INPUT_GUARDRAILS_ENABLED`: enables deterministic input guardrails for jailbreaks, high-stakes decisions, and unsafe requests.
- `WENJIA_LONG_TERM_MEMORY_ENABLED`: enables cross-session long-term memory keyed by the caller-supplied `client_id`.
- `WENJIA_TRACE_DIR`: local JSONL trace directory for inspecting routing, tool calls, latency, usage, and fallback.
- `WENJIA_OPENAI_SDK_TRACING`: enables OpenAI Agents SDK tracing; local JSONL tracing works independently by default.

## Python Usage

### Deterministic calculation

```python
from wenjia_agent.domain.bazi_adapter import BaziAdapter
from wenjia_agent.domain.schemas import BirthInfo

adapter = BaziAdapter()
result = adapter.calculate(
    BirthInfo(
        name="Demo",
        gender="unknown",
        birth_year=1995,
        birth_month=5,
        birth_day=12,
        birth_hour=9,
        birth_minute=30,
        calendar_type="solar",
        province="北京市",
        city="北京市",
    )
)

print(result.year_pillar, result.month_pillar, result.day_pillar, result.hour_pillar)
print(result.five_elements)
```

### Agent runner

```python
import asyncio

from wenjia_agent.runtime.runner import run_agent


async def main() -> None:
    response = await run_agent(
        session_id="demo-session",
        message="Please create a basic BaZi chart for someone born in Beijing at 09:30 on 1995-05-12.",
    )
    print(response)


asyncio.run(main())
```

## Project Layout

```text
wenjia_agent/        # Reusable agent core (importable package)
  agents/            # OpenAI Agents SDK Agent definitions
  core/              # Deterministic metaphysics logic
  domain/            # Pydantic schemas, adapters, context builders
  prompts/           # Versioned prompt templates
  runtime/           # Settings, runner, session helpers
  tools/             # OpenAI Agents SDK function tools
apps/                # First-class entry points (adapters over the core)
  web/
    backend/         # API-only FastAPI service (JSON + SSE)
    frontend/        # React + Ant Design X SPA
docs/                # Requirements, architecture, design, contribution docs
examples/            # CLI examples
tests/               # Unit tests
```

## Core Design

`wenjia-agent` separates deterministic metaphysics calculation from language
generation:

1. `wenjia_agent/core` and `wenjia_agent/domain` provide testable and reproducible calculation
   logic.
2. `wenjia_agent/agents` and `wenjia_agent/prompts` handle dialogue, clarification, explanation,
   and structured reports.

Key metaphysics fields must come from tools. Agents may explain tool results
and organize reports, but they should not invent BaZi pillars, five elements,
ten gods, or ShenSha data.

Personalized charting, fortune analysis, relationship analysis, naming, and
advice requests are gated by complete birth information. If required fields are
missing, Agents keep asking for the missing fields before continuing.

## Development

Windows PowerShell:

```powershell
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python scripts/run_evals.py
poetry run python -m compileall wenjia_agent examples tests
cd apps/web/frontend
npm run build
```

Linux:

```bash
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python scripts/run_evals.py
poetry run python -m compileall wenjia_agent examples tests
cd apps/web/frontend
npm run build
```

## Deployment

See the full [Deployment Guide](docs/DEPLOYMENT.md). The repository includes
three public deployment paths:

- `scripts/deploy_ubuntu.sh`: lightweight preview runner for servers that
  already have Python / Poetry / Node installed.
- `scripts/deploy_static_nginx.sh` + [nginx.example.conf](docs/deploy/nginx.example.conf):
  Nginx serves the static frontend and proxies FastAPI.
- [compose.yaml](compose.yaml): starts a backend container and frontend Nginx
  container with one command.

Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080.

## Documentation

| Document | Description |
| --- | --- |
| [Requirements](docs/REQUIREMENTS.md) | Product scope and acceptance criteria. |
| [Agent Proposal](docs/AGENT_PROPOSAL.md) | Agent project positioning and roadmap. |
| [Software Design](docs/SOFTWARE_DESIGN.md) | Technical design and implementation boundaries. |
| [Architecture](docs/ARCHITECTURE.md) | Module layout and runtime architecture. |
| [R&D Process](docs/RD_PROCESS.md) | Development workflow and release process. |
| [Agent Flow Visualization](docs/AGENT_FLOW_VISUALIZATION.md) | SSE event protocol and Web Demo visualization design. |
| [Development Guide](docs/DEVELOPMENT.md) | Local setup and day-to-day commands. |
| [Deployment Guide](docs/DEPLOYMENT.md) | Local, Ubuntu, Nginx, and Docker Compose deployment. |
| [Contributing Guide](docs/CONTRIBUTING.md) | Contribution rules and checklist. |
| [Tool Plugin Guide](docs/TOOL_PLUGIN_GUIDE.md) | Tool design and extension guide. |
| [Web App](apps/web/README.en.md) | Front/back-separated web app usage and endpoints. |
| [Security Policy](SECURITY.md) | Vulnerability reporting, sensitive data, and deployment security notes. |
| [Code of Conduct](CODE_OF_CONDUCT.md) | Community collaboration rules. |
| [Changelog](CHANGELOG.md) | Version history. |

## Contributing

Issues, prompt improvements, tool extensions, test cases, and documentation
updates are welcome. Please read the [Contributing Guide](docs/CONTRIBUTING.md)
and [Tool Plugin Guide](docs/TOOL_PLUGIN_GUIDE.md) first. Please also follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Report security issues privately
according to the [Security Policy](SECURITY.md).

## Responsible Use

Metaphysics content is for cultural entertainment and personal reference only.
For medical, legal, investment, mental health, or other high-stakes issues, use
real-world judgment and seek qualified professional help. Public deployers are
also responsible for authentication, rate limits, abuse monitoring, cost
controls, data retention, and compliance.

## License

Apache-2.0
