<div align="center">

<img src="docs/assets/wenjia-mark.svg" alt="wenjia-agent" width="96" height="96" />

# wenjia-agent

基于 OpenAI Agents SDK 的开源中文命理 Agent 项目。

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![OpenAI Agents SDK](https://img.shields.io/badge/OpenAI-Agents%20SDK-111111.svg)](https://github.com/openai/openai-agents-python)

[English](README.md) | [简体中文](README.zh-CN.md)

</div>

## 项目简介

`wenjia` 取“问甲”之意。`wenjia-agent` 面向中文命理场景，将确定性八字计算、OpenAI Agents SDK
编排、function tools、会话记忆、结构化报告和 Prompt 模板组织成一个轻量、
可扩展的 Python 工程。

核心思路很简单：命盘基础数据由本地工具确定性计算，Agent 负责追问、路由、
解释和结构化报告生成。

## 目录

- [特性](#特性)
- [Agent 拓扑](#agent-拓扑)
- [快速开始](#快速开始)
- [配置](#配置)
- [Python 用法](#python-用法)
- [项目结构](#项目结构)
- [开发](#开发)
- [文档](#文档)
- [负责任使用](#负责任使用)

## 特性

| 特性 | 说明 |
| --- | --- |
| 多 Agent 工作流 | 主控 Agent 负责路由，专门 Agent 负责具体任务。 |
| 出生信息门禁 | 个性化命理问题必须先提供完整出生信息，才能继续排盘或分析。 |
| 确定性八字核心 | 八字、真太阳时、五行、十神、纳音、神煞、空亡、命宫等结果由本地逻辑计算。 |
| 工具优先推理 | Agent 通过 function tools 获取命盘数据，避免由模型自行推算关键命理字段。 |
| 结构化输出 | 命格、关系、起名报告使用 Pydantic schema 约束，方便上层应用集成。 |
| Prompt-as-code | 长提示词位于 `app/prompts`，支持版本化维护和社区协作。 |
| 会话记忆 | 基于 `SQLAlchemySession` 提供 Agent 会话记忆。 |
| Poetry 工作流 | 内置 CLI 示例、测试、lint 和开发文档。 |

## Agent 拓扑

| Agent | 职责 |
| --- | --- |
| `WenjiaMainAgent` | 识别用户意图，并将任务移交给专门 Agent。 |
| `ProfileAgent` | 收集出生资料、查询城市、生成基础八字命盘。 |
| `FortuneAgent` | 生成命格、事业、财富、关系和行动建议分析。 |
| `RelationshipAgent` | 分析合盘、关系模式和沟通建议。 |
| `NamingAgent` | 生成中文起名策略和名字建议。 |
| `MysticToolsAgent` | 解释工具字段、查询支持地区、排查参数问题。 |

```text
WenjiaMainAgent
  ├─ ProfileAgent
  ├─ FortuneAgent
  ├─ RelationshipAgent
  ├─ NamingAgent
  └─ MysticToolsAgent
```

## 快速开始

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

### 运行确定性八字 Demo

该 Demo 调用本地八字核心，不需要 API key。

Windows PowerShell:

```powershell
poetry run python examples\cli_bazi.py
```

Linux:

```bash
poetry run python examples/cli_bazi.py
```

示例输出：

```text
四柱八字：
乙亥 辛巳 癸卯 丁巳
五行分布： {'木': 3, '火': 6, '土': 1, '金': 3, '水': 3}
```

### 运行 Agent CLI

先在 `.env` 中填写 `OPENAI_API_KEY`。

Windows PowerShell:

```powershell
poetry run python examples\cli_agent.py
```

Linux:

```bash
poetry run python examples/cli_agent.py
```

### 运行 Web Demo

Web Demo 提供浏览器聊天界面，后端复用同一个 Agent runner。

Windows PowerShell:

```powershell
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

Linux:

```bash
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

## 配置

从 `.env.example` 创建 `.env`，并配置运行时参数：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

## Python 用法

### 确定性排盘

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

### Agent Runner

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

## 项目结构

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

## 核心设计

`wenjia-agent` 将确定性命理计算和语言生成分离：

1. `app/core` 与 `app/domain` 提供可测试、可复现的计算逻辑。
2. `app/agents` 与 `app/prompts` 负责对话、追问、解释和结构化报告。

关键命理字段必须通过工具获得。Agent 可以解释工具结果、整理报告、补充语境
和建议，但不直接编造四柱、五行、十神、神煞等基础数据。

排盘、命格分析、合盘、起名和个性化建议都需要先经过完整出生信息门禁。
如果缺少必要字段，Agent 会持续追问缺失信息，再继续处理请求。

## 开发

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

## 文档

| 文档 | 说明 |
| --- | --- |
| [需求报告](docs/REQUIREMENTS.md) | 产品范围和验收标准。 |
| [Agent 策划书](docs/AGENT_PROPOSAL.md) | Agent 项目定位和路线图。 |
| [软件设计文档](docs/SOFTWARE_DESIGN.md) | 技术设计和实现边界。 |
| [架构说明](docs/ARCHITECTURE.md) | 模块布局和运行时架构。 |
| [研发流程](docs/RD_PROCESS.md) | 开发工作流和发布流程。 |
| [Agent 流程可视化](docs/AGENT_FLOW_VISUALIZATION.md) | SSE 事件协议和 Web Demo 可视化设计。 |
| [开发指南](docs/DEVELOPMENT.md) | 本地环境和日常命令。 |
| [贡献指南](docs/CONTRIBUTING.md) | 贡献规则和检查清单。 |
| [工具插件指南](docs/TOOL_PLUGIN_GUIDE.md) | 工具设计和扩展指南。 |
| [Web Demo](examples/web/README.md) | 浏览器聊天 Demo 用法和接口说明。 |

## 贡献

欢迎提交 issue、Prompt 改进、工具扩展、测试用例和文档更新。建议先阅读
[贡献指南](docs/CONTRIBUTING.md) 和 [工具插件指南](docs/TOOL_PLUGIN_GUIDE.md)。

## 负责任使用

命理内容仅作文化娱乐与个人参考。涉及医疗、法律、投资、心理危机等高风险
问题时，应结合现实情况并寻求专业帮助。

## License

Apache-2.0
