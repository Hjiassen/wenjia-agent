# wenjia-agent

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![OpenAI Agents SDK](https://img.shields.io/badge/OpenAI-Agents%20SDK-111111.svg)](https://github.com/openai/openai-agents-python)

[中文](#中文) | [English](#english)

## 中文

面向中文命理场景的开源 Agent 项目。`wenjia-agent` 使用 OpenAI Agents SDK 构建多 Agent 工作流，将确定性八字计算、工具调用、会话记忆、结构化报告和 Prompt 模板组织成一个轻量、可扩展的 Python 工程。

### 特性

- **多 Agent 工作流**：主控 Agent 负责路由，专门 Agent 负责排盘、命格分析、关系合盘、起名建议和工具查询。
- **确定性八字核心**：八字、真太阳时、五行、十神、纳音、神煞、空亡、命宫等结果由本地逻辑计算。
- **工具优先推理**：Agent 通过 function tools 获取命盘数据，避免由模型自行推算关键命理字段。
- **结构化输出**：命格、关系、起名报告使用 Pydantic schema 约束，方便上层应用集成。
- **Prompt-as-code**：长提示词放在 `app/prompts`，支持版本化维护和社区协作。
- **会话记忆**：基于 `SQLAlchemySession` 提供 Agent 会话记忆。
- **Poetry 工作流**：内置 CLI 示例、测试、lint 和开发文档。

### Agent 拓扑

```text
WenjiaMainAgent
  ├─ ProfileAgent        # 出生资料收集、城市查询、基础排盘
  ├─ FortuneAgent        # 命格、事业、财富、感情、行动建议
  ├─ RelationshipAgent   # 合盘、关系模式、沟通建议
  ├─ NamingAgent         # 中文起名策略与名字建议
  └─ MysticToolsAgent    # 工具查询、字段解释、参数排障
```

### 环境要求

- Python 3.11+
- Poetry 1.8+

### 安装

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

在 `.env` 中配置：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

### 启动

确定性八字 Demo 不需要 API key。

Windows PowerShell:

```powershell
poetry run python examples\cli_bazi.py
```

Linux:

```bash
poetry run python examples/cli_bazi.py
```

Agent CLI 需要先在 `.env` 中填写 `OPENAI_API_KEY`。

Windows PowerShell:

```powershell
poetry run python examples\cli_agent.py
```

Linux:

```bash
poetry run python examples/cli_agent.py
```

示例输出：

```text
四柱八字：
乙亥 辛巳 癸卯 丁巳
五行分布： {'木': 3, '火': 6, '土': 1, '金': 3, '水': 3}
```

### Python 用法

确定性排盘：

```python
from app.domain.bazi_adapter import BaziAdapter
from app.domain.schemas import BirthInfo

adapter = BaziAdapter()
result = adapter.calculate(
    BirthInfo(
        name="示例",
        gender="未知",
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

Agent Runner：

```python
import asyncio

from app.runtime.runner import run_agent


async def main() -> None:
    response = await run_agent(
        session_id="demo-session",
        message="帮我看一下 1995 年 5 月 12 日上午 9:30 北京出生的基础命盘。",
    )
    print(response)


asyncio.run(main())
```

### 项目结构

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
tests/         # Unit tests
```

### 核心设计

`wenjia-agent` 将命理计算和语言生成分成两层：

1. `app/core` 与 `app/domain` 负责可测试、可复现的确定性计算。
2. `app/agents` 与 `app/prompts` 负责对话、追问、解释和结构化报告。

关键命理字段必须通过工具获得。Agent 可以解释工具结果、整理报告、补充语境和建议，但不直接编造四柱、五行、十神、神煞等基础数据。

### 开发命令

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

### 文档

- [需求报告](docs/REQUIREMENTS.md)
- [Agent 策划书](docs/AGENT_PROPOSAL.md)
- [软件设计文档](docs/SOFTWARE_DESIGN.md)
- [架构说明](docs/ARCHITECTURE.md)
- [研发流程](docs/RD_PROCESS.md)
- [开发指南](docs/DEVELOPMENT.md)
- [贡献指南](docs/CONTRIBUTING.md)
- [工具插件指南](docs/TOOL_PLUGIN_GUIDE.md)

### 贡献

欢迎提交 issue、Prompt 改进、工具扩展、测试用例和文档改进。建议先阅读 [贡献指南](docs/CONTRIBUTING.md) 与 [工具插件指南](docs/TOOL_PLUGIN_GUIDE.md)。

### 负责任使用

命理内容仅作文化娱乐与个人参考。涉及医疗、法律、投资、心理危机等高风险问题时，应结合现实情况并寻求专业帮助。

## English

`wenjia-agent` is an open-source Agent project for Chinese metaphysics scenarios. It uses the OpenAI Agents SDK to build a multi-agent workflow around deterministic BaZi calculation, function tools, session memory, structured reports, and prompt templates.

### Features

- **Multi-agent workflow**: A main routing Agent delegates tasks to specialized Agents for profiling, fortune analysis, relationship analysis, naming, and tool support.
- **Deterministic BaZi core**: BaZi pillars, true solar time, five elements, ten gods, NaYin, ShenSha, KongWang, and life-palace fields are calculated locally.
- **Tool-first reasoning**: Agents retrieve chart data through function tools instead of asking the model to infer key metaphysics fields.
- **Structured outputs**: Fortune, relationship, and naming reports are constrained by Pydantic schemas.
- **Prompt-as-code**: Long prompts live in `app/prompts` for versioned maintenance and community collaboration.
- **Session memory**: Agent conversation memory is backed by `SQLAlchemySession`.
- **Poetry workflow**: The project includes CLI examples, tests, linting, and development docs.

### Agent Topology

```text
WenjiaMainAgent
  ├─ ProfileAgent        # Birth profile collection, city lookup, basic charting
  ├─ FortuneAgent        # Fortune, career, wealth, relationship, action advice
  ├─ RelationshipAgent   # Compatibility, relationship patterns, communication advice
  ├─ NamingAgent         # Chinese naming strategy and suggestions
  └─ MysticToolsAgent    # Tool lookup, field explanation, parameter troubleshooting
```

### Requirements

- Python 3.11+
- Poetry 1.8+

### Installation

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

Configure `.env`:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

### Run

The deterministic BaZi demo does not require an API key.

Windows PowerShell:

```powershell
poetry run python examples\cli_bazi.py
```

Linux:

```bash
poetry run python examples/cli_bazi.py
```

The Agent CLI requires `OPENAI_API_KEY` in `.env`.

Windows PowerShell:

```powershell
poetry run python examples\cli_agent.py
```

Linux:

```bash
poetry run python examples/cli_agent.py
```

Example output:

```text
四柱八字：
乙亥 辛巳 癸卯 丁巳
五行分布： {'木': 3, '火': 6, '土': 1, '金': 3, '水': 3}
```

### Python Usage

Deterministic calculation:

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

Agent runner:

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

### Project Layout

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
tests/         # Unit tests
```

### Core Design

`wenjia-agent` separates deterministic metaphysics calculation from language generation:

1. `app/core` and `app/domain` provide testable and reproducible calculation logic.
2. `app/agents` and `app/prompts` handle dialogue, clarification, explanation, and structured reports.

Key metaphysics fields must come from tools. Agents may explain tool results and organize reports, but they should not invent BaZi pillars, five elements, ten gods, or ShenSha data.

### Development

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

### Documentation

- [Requirements](docs/REQUIREMENTS.md)
- [Agent Proposal](docs/AGENT_PROPOSAL.md)
- [Software Design](docs/SOFTWARE_DESIGN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [R&D Process](docs/RD_PROCESS.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Contributing Guide](docs/CONTRIBUTING.md)
- [Tool Plugin Guide](docs/TOOL_PLUGIN_GUIDE.md)

### Contributing

Issues, prompt improvements, tool extensions, test cases, and documentation updates are welcome. Please read the [Contributing Guide](docs/CONTRIBUTING.md) and [Tool Plugin Guide](docs/TOOL_PLUGIN_GUIDE.md) first.

### Responsible Use

Metaphysics content is for cultural entertainment and personal reference only. For medical, legal, investment, mental health, or other high-stakes issues, use real-world judgment and seek qualified professional help.

## License

Apache-2.0
