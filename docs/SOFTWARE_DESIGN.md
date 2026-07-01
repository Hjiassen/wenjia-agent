# 软件设计文档

## 技术选型

- Python 3.11+
- OpenAI Agents SDK
- `SQLAlchemySession`
- Pydantic v2
- Poetry
- pytest
- ruff

## 分层设计

```text
agents -> tools -> domain -> core
```

- `agents`：定义 Agent、handoff、模型、结构化输出。
- `tools`：OpenAI function tool wrapper。
- `domain`：schema、adapter、context builder。
- `core`：八字和城市数据等确定性逻辑。

## Agent 设计

`WenjiaMainAgent` 只做任务理解和路由，避免把所有能力塞进一个 prompt。

专门 Agent：

- `ProfileAgent` 使用排盘工具，负责基础命盘输出。
- `FortuneAgent` 使用 `FortuneReport` 输出命格报告。
- `RelationshipAgent` 使用 `RelationshipReport` 输出关系分析。
- `NamingAgent` 使用 `NamingReport` 输出起名建议。
- `MysticToolsAgent` 负责工具查询和字段解释。

## 工具设计

工具返回统一 envelope：

```python
{
    "ok": True,
    "tool_name": "calculate_bazi",
    "data": {},
    "message": None,
    "warnings": [],
}
```

关键工具：

- `calculate_bazi_tool`
- `validate_birth_info_tool`
- `build_bazi_context_tool`
- `list_provinces_tool`
- `list_cities_tool`

## 出生信息门禁

所有个性化命理请求在排盘或分析前都需要确认完整出生信息。完整信息包括：

- 姓名或展示名
- 性别
- 出生年、月、日、小时、分钟
- 历法类型：公历或农历
- 出生地省市或出生地经度
- 农历日期需确认是否闰月

Agent 在处理排盘、命格分析、合盘、起名和个性化建议前，应先调用或参考
`validate_birth_info_tool`。如果缺少任一字段，只返回缺失字段追问，不进入
排盘、分析或报告生成流程。

## 命盘上下文

`build_bazi_context_tool` 会把原始排盘结果整理成：

- 四柱
- 实际公历日期
- 真太阳时
- 五行强弱摘要
- 十神
- 纳音
- 神煞
- 空亡
- 胎元、命宫、身宫、太息
- warnings

分析类 Agent 必须基于该上下文生成报告。

## Session 设计

默认使用：

```text
sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

Session 只保存 Agent 对话记忆，不代表用户账号。外部产品可以用自己的业务 ID 映射 `session_id`。

## Prompt 设计

Prompt 文件位于 `wenjia_agent/prompts`，通过 `load_prompt` 加载。每个 prompt 使用 front matter 标记：

```yaml
id: fortune_analysis
version: 0.1.0
owner: wenjia-agent
status: active
```

## 风险控制

- Agent 不自行推算八字。
- 工具 warning 必须进入回复。
- 不输出确定性承诺或恐吓式判断。
- 医疗、法律、投资、心理危机等高风险问题必须建议寻求专业帮助。

## 扩展方式

新增能力时优先新增专门 Agent 或工具，而不是膨胀主 Agent。

新增确定性算法放在 `wenjia_agent/core` 或 `wenjia_agent/domain`；新增生成式能力放在 `wenjia_agent/agents` 和 `wenjia_agent/prompts`。
