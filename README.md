<div align="center">

# wenjia-agent

Open-source Chinese metaphysics Agents powered by the OpenAI Agents SDK.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![OpenAI Agents SDK](https://img.shields.io/badge/OpenAI-Agents%20SDK-111111.svg)](https://github.com/openai/openai-agents-python)

[English](README.md) | [简体中文](README.zh-CN.md)

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

- [Features](#features)
- [Agent Topology](#agent-topology)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Python Usage](#python-usage)
- [Project Layout](#project-layout)
- [Development](#development)
- [Documentation](#documentation)
- [Responsible Use](#responsible-use)

## Features

| Feature | Description |
| --- | --- |
| Multi-agent workflow | A main routing Agent delegates work to specialized Agents. |
| Birth info gate | Personalized metaphysics requests must provide a complete birth profile before analysis. |
| Deterministic BaZi core | BaZi pillars, true solar time, five elements, ten gods, NaYin, ShenSha, KongWang, and life-palace fields are calculated locally. |
| Tool-first reasoning | Agents retrieve chart data through function tools instead of inferring key metaphysics fields directly. |
| Structured outputs | Fortune, relationship, and naming reports are constrained by Pydantic schemas. |
| Prompt-as-code | Long prompts live in `app/prompts` for versioned maintenance and community collaboration. |
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

### Run the Web demo

The Web demo provides a browser chat interface backed by the same Agent runner.

Windows PowerShell:

```powershell
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

Linux:

```bash
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Configuration

Create `.env` from `.env.example` and configure the runtime values:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

## Python Usage

### Deterministic calculation

```python
from app.domain.bazi_adapter import BaziAdapter
from app.domain.schemas import BirthInfo

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

from app.runtime.runner import run_agent


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
app/
  agents/      # OpenAI Agents SDK Agent definitions
  core/        # Deterministic metaphysics logic
  domain/      # Pydantic schemas, adapters, context builders
  prompts/     # Versioned prompt templates
  runtime/     # Settings, runner, session helpers
  tools/       # OpenAI Agents SDK function tools
docs/          # Requirements, architecture, design, contribution docs
examples/      # CLI examples
  web/         # FastAPI web chat demo
tests/         # Unit tests
```

## Core Design

`wenjia-agent` separates deterministic metaphysics calculation from language
generation:

1. `app/core` and `app/domain` provide testable and reproducible calculation
   logic.
2. `app/agents` and `app/prompts` handle dialogue, clarification, explanation,
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
poetry run python -m compileall app examples tests
```

Linux:

```bash
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python -m compileall app examples tests
```

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
| [Contributing Guide](docs/CONTRIBUTING.md) | Contribution rules and checklist. |
| [Tool Plugin Guide](docs/TOOL_PLUGIN_GUIDE.md) | Tool design and extension guide. |
| [Web Demo](examples/web/README.md) | Browser chat demo usage and endpoints. |

## Contributing

Issues, prompt improvements, tool extensions, test cases, and documentation
updates are welcome. Please read the [Contributing Guide](docs/CONTRIBUTING.md)
and [Tool Plugin Guide](docs/TOOL_PLUGIN_GUIDE.md) first.

## Responsible Use

Metaphysics content is for cultural entertainment and personal reference only.
For medical, legal, investment, mental health, or other high-stakes issues, use
real-world judgment and seek qualified professional help.

## License

Apache-2.0
