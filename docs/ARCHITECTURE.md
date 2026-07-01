# Architecture

`wenjia-agent` 是单仓库、纯 Agent 模块。它提供可嵌入的命理 Agent 能力，不提供账号、认证、支付、订单、会员或运营后台。

```text
CLI / Web Demo / SDK Caller
    |
    v
OpenAI Agents SDK Runner
    |
    v
WenjiaMainAgent
    |
    +--> ProfileAgent
    +--> FortuneAgent
    +--> RelationshipAgent
    +--> NamingAgent
    +--> MysticToolsAgent
    |
    +--> Function Tools
            |
            v
        Domain Adapters / Context Builders
            |
            v
        wenjia_agent/core deterministic logic
```

## 模块边界

### `wenjia_agent/core`

确定性命理逻辑：

- 八字排盘
- 真太阳时
- 农历/公历转换
- 五行
- 十神
- 纳音
- 神煞
- 空亡
- 城市经纬度

`wenjia_agent/core` 不允许调用 LLM。

### `wenjia_agent/domain`

确定性逻辑和 Agent 之间的类型边界：

- Pydantic schemas
- `BaziAdapter`
- `context_builders`
- Fortune / Relationship / Naming 结构化报告模型

### `wenjia_agent/tools`

OpenAI Agents SDK function tools。工具暴露给 Agent，但内部仍调用确定性 adapter 或 context builder。

当前工具：

- `calculate_bazi_tool`
- `build_bazi_context_tool`
- `list_provinces_tool`
- `list_cities_tool`

### `wenjia_agent/agents`

Agent 定义：

- `WenjiaMainAgent`
- `ProfileAgent`
- `FortuneAgent`
- `RelationshipAgent`
- `NamingAgent`
- `MysticToolsAgent`

分析类 Agent 使用 Pydantic `output_type` 约束结构化输出。

### `wenjia_agent/prompts`

版本化 prompt 模板，由 `wenjia_agent.prompts.load_prompt` 加载。

当前模板：

- `main_agent.md`
- `profile_agent.md`
- `fortune_analysis.md`
- `relationship_agent.md`
- `naming_agent.md`
- `mystic_tools_agent.md`

### `wenjia_agent/runtime`

运行时配置和 `SQLAlchemySession` runner helper。默认会话数据库：

```text
sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

Session 只用于 Agent 对话记忆，不代表用户账号，不提供认证或权限能力。

## 数据流

1. 调用方发送自然语言输入。
2. `WenjiaMainAgent` 判断任务类型。
3. 主控 Agent handoff 到专门 Agent。
4. 专门 Agent 缺资料时追问，资料完整时调用工具。
5. 工具通过 `BaziAdapter` 调用 `wenjia_agent/core`。
6. `build_bazi_context_tool` 将命盘整理成 Agent 友好的确定性上下文。
7. 分析类 Agent 基于上下文生成结构化报告。

## 非目标

本仓库不实现：

- 用户账号
- 登录认证
- 支付
- 订单
- 会员
- 运营/admin 后台
