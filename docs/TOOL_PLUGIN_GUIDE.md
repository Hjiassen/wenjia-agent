# Tool Plugin Guide

`wenjia-agent` 的工具应保持小、明确、可测试。工具是 Agent 与确定性命理核心之间的稳定契约。

## 工具分类

| Category | Examples | LLM Allowed |
| --- | --- | --- |
| deterministic | 八字排盘、城市查询、五行统计 | No |
| context | 命盘上下文整理、字段格式化 | No |
| generative | 命格报告、起名建议、关系分析 | Yes, through Agents |

## 当前工具

- `calculate_bazi_tool`：返回四柱、真太阳时、五行、十神、纳音、神煞、空亡等确定性结果。
- `build_bazi_context_tool`：在排盘结果上整理 Agent 分析上下文。
- `list_provinces_tool`：查询支持的省份/地区。
- `list_cities_tool`：查询省份下支持的城市。

## 确定性工具规则

确定性工具必须：

- 放在 `app/tools`。
- 调用 `app/core` 或 `app/domain` 中的薄 adapter/context builder。
- 相同输入返回稳定输出。
- 不调用 LLM。
- 有单元测试。

## 生成式能力规则

生成式能力应通过 Agent 实现，而不是藏在普通工具函数里：

- 使用 `app/prompts` 中的模板。
- 使用 Pydantic schemas 约束结构化输出。
- 加入解析、导入或数据形状测试。
- 明确文化娱乐和高风险建议边界。

## Function Tool Pattern

```python
from agents import function_tool


@function_tool
def my_tool(value: str) -> dict:
    """Short tool description visible to the Agent."""

    return {"ok": True, "data": value}
```

推荐同时保留一个不带装饰器的内部函数，方便单元测试：

```python
def my_tool_data(value: str) -> dict:
    return {"ok": True, "data": value}
```

## 边界

不要添加：

- 用户账号工具
- 认证工具
- 支付工具
- 订单工具
- 会员工具
- 运营/admin 工具

外部应用应提供这些能力，并把 `wenjia-agent` 作为嵌入式 Agent 模块调用。
