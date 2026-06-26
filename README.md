# wenjia-agent

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![OpenAI Agents SDK](https://img.shields.io/badge/OpenAI-Agents%20SDK-111111.svg)](https://github.com/openai/openai-agents-python)

面向中文命理场景的开源 Agent 项目。`wenjia-agent` 使用 OpenAI Agents SDK 构建多 Agent 工作流，将确定性八字计算、工具调用、会话记忆、结构化报告和 Prompt 模板组织成一个轻量、可扩展的 Python 工程。

## Highlights

- **Multi-agent workflow**：主控 Agent 负责路由，专门 Agent 负责排盘、命格分析、关系合盘、起名建议和工具查询。
- **Deterministic BaZi core**：八字、真太阳时、五行、十神、纳音、神煞、空亡、命宫等结果由本地确定性逻辑计算。
- **Tool-first reasoning**：Agent 通过 function tools 获取命盘数据，避免由模型自行推算关键命理字段。
- **Structured outputs**：命格、关系、起名报告使用 Pydantic schema 约束，方便上层应用集成。
- **Prompt-as-code**：所有长提示词放在 `app/prompts`，支持版本化维护和社区协作。
- **Session memory**：基于 `SQLAlchemySession` 提供 Agent 会话记忆。
- **Poetry workflow**：内置 CLI 示例、测试、lint 和开发文档。

## Agent Topology

```text
WenjiaMainAgent
  ├─ ProfileAgent        # 出生资料收集、城市查询、基础排盘
  ├─ FortuneAgent        # 命格、事业、财富、感情、行动建议
  ├─ RelationshipAgent   # 合盘、关系模式、沟通建议
  ├─ NamingAgent         # 中文起名策略与名字建议
  └─ MysticToolsAgent    # 工具查询、字段解释、参数排障
```

## Installation

要求：

- Python 3.11+
- Poetry 1.8+

```powershell
git clone <your-repo-url> wenjia-agent
cd wenjia-agent
poetry install --with dev
Copy-Item .env.example .env
```

在 `.env` 中配置：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

## Quick Start

### Run deterministic BaZi demo

该示例只调用本地八字核心，不需要 API key。

```powershell
poetry run python examples\cli_bazi.py
```

示例输出：

```text
四柱八字：
乙亥 辛巳 癸卯 丁巳
五行分布： {'木': 3, '火': 6, '土': 1, '金': 3, '水': 3}
```

### Run Agent CLI

先在 `.env` 中填写 `OPENAI_API_KEY`，然后运行：

```powershell
poetry run python examples\cli_agent.py
```

## Python Usage

### Deterministic calculation

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

### Agent runner

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
tests/         # Unit tests
```

## Core Design

`wenjia-agent` 将命理计算和语言生成分成两层：

1. `app/core` 与 `app/domain` 负责可测试、可复现的确定性计算。
2. `app/agents` 与 `app/prompts` 负责对话、追问、解释和结构化报告。

关键命理字段必须通过工具获得。Agent 可以解释工具结果、整理报告、补充语境和建议，但不直接编造四柱、五行、十神、神煞等基础数据。

## Prompt Templates

Prompt 模板位于 `app/prompts`：

- `main_agent.md`
- `profile_agent.md`
- `fortune_analysis.md`
- `relationship_agent.md`
- `naming_agent.md`
- `mystic_tools_agent.md`

## Development

```powershell
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python -m compileall app examples tests
```

## Documentation

- [需求报告](docs/REQUIREMENTS.md)
- [Agent 策划书](docs/AGENT_PROPOSAL.md)
- [软件设计文档](docs/SOFTWARE_DESIGN.md)
- [架构说明](docs/ARCHITECTURE.md)
- [研发流程](docs/RD_PROCESS.md)
- [开发指南](docs/DEVELOPMENT.md)
- [贡献指南](docs/CONTRIBUTING.md)
- [工具插件指南](docs/TOOL_PLUGIN_GUIDE.md)

## Contributing

欢迎提交 issue、prompt 改进、工具扩展、测试用例和文档改进。建议先阅读 [贡献指南](docs/CONTRIBUTING.md) 与 [工具插件指南](docs/TOOL_PLUGIN_GUIDE.md)。

## Responsible Use

命理内容仅作文化娱乐与个人参考。涉及医疗、法律、投资、心理危机等高风险问题时，应结合现实情况并寻求专业帮助。

## License

Apache-2.0
