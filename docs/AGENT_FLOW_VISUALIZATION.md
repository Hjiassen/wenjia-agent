# Agent 流程可视化设计

本文记录 `wenjia-agent` 的 Agent 执行过程可视化设计。参考项目为
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)。

## 参考项目解读

`daily_stock_analysis` 采用“后端事件流 + 前端时间线”的模式：

1. 后端提供 `POST /api/v1/agent/chat/stream`。
2. Agent runner 在执行过程中输出进度事件。
3. API 将事件包装成 SSE：`data: {...}\n\n`。
4. 前端通过 `fetch` 和 `ReadableStream` 读取事件。
5. 当前助手消息保存 `thinkingSteps`，并渲染成可折叠的“思考过程”。

核心事件包括 `thinking`、`tool_start`、`tool_done`、`generating`、`done` 和
`error`。该项目还包含更重的 `RunFlow` 拓扑模型，包含 `lane`、`node`、`edge`
和 `event`。问甲第一阶段先复刻轻量时间线。

## 问甲实现方式

`wenjia-agent` 使用 OpenAI Agents SDK，不重新实现 Agent runner。后端通过以下
SDK 能力转换生命周期事件：

- `Runner.run_streamed`
- `RunHooksBase`
- `SQLAlchemySession`
- `stream_events()`

前端只依赖问甲自己的事件协议，不直接依赖 SDK 内部事件结构。

## 事件协议

`POST /api/chat/stream` 返回 `text/event-stream`。每个事件是一个 JSON 对象：

```json
{
  "id": "web:session-id:3",
  "session_id": "web:session-id",
  "timestamp": "2026-06-29T00:00:00+00:00",
  "type": "tool_done",
  "tool": "validate_birth_info_tool",
  "display_name": "出生信息完整性检查",
  "success": true,
  "duration": 0.03,
  "message": "出生信息完整性检查完成。"
}
```

| 事件 | 触发时机 |
| --- | --- |
| `run_start` | 收到用户消息后。 |
| `agent_start` | SDK 即将调用某个 Agent。 |
| `thinking` | LLM 调用前。 |
| `handoff` | Agent 发生移交。 |
| `tool_start` | 本地工具调用前。 |
| `tool_done` | 本地工具调用后。 |
| `generating` | Agent 产出最终输出时。 |
| `done` | 本轮执行完成。 |
| `error` | 执行异常。 |

## 展示映射

| SDK 名称 | 展示名 |
| --- | --- |
| `WenjiaMainAgent` | 主控路由 |
| `ProfileAgent` | 出生资料与排盘 |
| `FortuneAgent` | 命格分析 |
| `RelationshipAgent` | 关系合盘 |
| `NamingAgent` | 起名建议 |
| `MysticToolsAgent` | 工具查询 |

| 工具 | 展示名 |
| --- | --- |
| `validate_birth_info_tool` | 出生信息完整性检查 |
| `calculate_bazi_tool` | 确定性八字排盘 |
| `build_bazi_context_tool` | 命盘上下文构建 |
| `list_provinces_tool` | 支持省份查询 |
| `list_cities_tool` | 支持城市查询 |

## Web App 行为

Web App（`apps/web/frontend`，基于 Ant Design X）调用 `/api/chat/stream`。每个
SSE 事件通过 `lib/flowModel.ts::buildPipeline` 归约成阶段（stage），并渲染为每条
助手气泡下方的 **ThoughtChain**（思考链）：`success→success`、`failed→error`、
`active/pending→带 spinner 的 pending`。收到 `done` 后写入最终回答（Markdown），
并把完整事件流随消息保存到浏览器历史记录。

## 边界

流程事件只展示 Agent、工具、状态、耗时和通用文案，不输出工具入参，因此不会在
时间线中暴露姓名、生日、出生地、经度等出生资料。

## 后续扩展

下一阶段可以基于同一事件协议生成拓扑图：

```text
用户问题 -> 主控路由 -> 出生信息门禁 -> 专门 Agent -> 确定性工具 -> 回答生成
```
