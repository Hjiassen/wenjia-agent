# 问甲 Agent 优化需求文档

> 版本：v0.1 ·  状态：草案 ·  范围：在现有 wenjia-agent 基础上的系统性优化
> 目标读者：本项目维护者 / 贡献者

## 实现进度

- ✅ **第二期 Agent Harness + Loop（已落地）**：`app/harness/`（`policy` + `loop`，Act→Verify→Revise→Finalize），包裹 SDK Runner，`runner.py` / `stream_runner.py` 已接线；前端运行流弹窗展示 `revise`/`verify` 节点。
- ✅ **A3 Guardrails（输出护栏，已落地）**：`app/guardrails/output_checks.py`——空回复、边界提醒、绝对化/恐吓措辞、八字一致性，纯函数可离线测试。
- ✅ **A6 报告事实校验（已落地）**：八字一致性校验联动 Verify–Revise，不一致触发修订。
- ⏳ 待办：A1 Evals、A2 Tracing、B1 CI、B5 韧性（超时/fallback）、A4 流式、A5 记忆、C 领域工具等。

## 0. 背景与目标

wenjia-agent 当前已具备：OpenAI Agents SDK 的 handoff 多智能体（主控路由 + 排盘/命格/合盘/起名/工具查询）、确定性八字工具、会话记忆（SQLAlchemySession）+ 人物档案表（`wenjia_profiles`）、FastAPI + React 演示前端（流程卡片可视化）、提示词模板、基础 pytest、工具去重与 max_turns 兜底、结构化报告的 Markdown 渲染。

作为一个**严肃的 Agent 项目**，距离「可评测、可观测、可上线、可扩展」仍有差距。本文件梳理优化需求，并重点引入近期较火的 **Agent Harness + Loop** 架构范式，将当前「隐式、依赖 SDK 的执行流」升级为「显式、可控、可验证、可回归」的智能体执行框架。

衡量成功的北极星指标：
- **正确性**：报告中的确定性事实（四柱/五行/神煞）与工具计算 100% 一致；出生信息门禁不被绕过。
- **可观测**：每一次运行可追踪 token/成本/延迟/工具调用链。
- **可回归**：换模型 / 改提示词后，能用离线评测量化质量变化。
- **稳定**：弱模型或 provider 故障下不死循环、不卡死、优雅降级。

---

## 1. 现状快照

| 维度 | 现状 |
| --- | --- |
| 编排 | SDK handoff 隐式 agent loop；`max_turns=16` 兜底；工具去重 `WenjiaRunContext.tool_cache` |
| 记忆 | 按 session 的 SQLAlchemy 会话记忆 + `wenjia_profiles` 档案表（sqlite，`create_all`） |
| 工具 | 排盘 / 五行 / 十神 / 神煞 / 城市 / 存档 / 列档案 |
| 评测 | 仅 mock 掉 LLM 的单测，**无智能体质量评测** |
| 可观测 | `tracing_disabled=True`，flow 事件仅供前端 UI |
| 护栏 | `app/guardrails/` **空目录** |
| 流式 | 仅推送生命周期事件，最终答案一次性返回 |
| 上线 | 无 CI、无 Docker、无迁移、API 无鉴权/限流 |

---

## 2. 优化需求清单

> 每条：`现状 → 目标 → 方案要点 → 验收标准 → 优先级（P0 最高）`

### A. Agent 核心能力

**A1. 评测体系（Evals）· P0**
- 现状：无任何衡量智能体质量的手段。
- 目标：可量化路由准确率、工具调用正确性、出生信息门禁命中率、事实一致性、报告质量。
- 方案：建 `evals/` —— 一组 golden 对话用例（输入 + 期望路由/工具/断言）+ 离线 runner + LLM-as-judge 打分；输出分项报告。
- 验收：`make eval` 跑出一份分数报告；CI 中对关键指标设阈值。

**A2. 可观测性 / Tracing · P0**
- 现状：tracing 关闭，无成本/延迟/调用链记录。
- 目标：每次 run 可追踪 agent/tool 调用链、token、成本、延迟、错误。
- 方案：开启 SDK tracing 或接入 OpenTelemetry / Langfuse；结构化日志；在 `WenjiaRunContext` 累计 token 与耗时。
- 验收：本地与生产可查看单次 run 的完整 trace 与成本。

**A3. Guardrails（护栏）· P0**
- 现状：`app/guardrails/` 空。
- 目标：输入与输出双向护栏。
- 方案：
  - 输入：越狱/敏感话题/超范围请求拦截（SDK `InputGuardrail`）。
  - 输出：必须含 `boundary_note`；禁止医疗/法律/投资的确定性承诺与恐吓措辞；命盘事实与工具结果一致（见 A6）。
- 验收：构造违规用例被拦截或纠正；护栏命中写入 trace。

**A4. 逐字流式输出 · P1**
- 现状：最终答案一次性 `done` 事件。
- 目标：token-by-token 流式渲染。
- 方案：消费 SDK 的文本增量事件（`ResponseTextDeltaEvent` 等），新增 `delta` 事件类型，前端增量拼接。
- 验收：长报告边生成边显示。

**A5. 上下文 / 长期记忆管理 · P1**
- 现状：仅原始会话记忆，长对话会撑爆上下文。
- 目标：上下文窗口安全 + 跨会话长期记忆。
- 方案：对历史做滚动摘要/裁剪；档案表已存事实优先复用；可选向量记忆。
- 验收：超长对话不超限、不丢关键事实。

**A6. 报告事实校验 · P0（与 A3 联动）**
- 现状：报告 prose 里的四柱/五行可能与工具结果不符。
- 目标：确定性字段零幻觉。
- 方案：生成后用「报告 vs 工具输出」结构化比对；不一致则进入修订 loop（见第 3 节）。
- 验收：注入错误命盘的对照测试能被检出并纠正。

### B. 工程化与上线

| 编号 | 需求 | 现状 → 目标 | 优先级 |
| --- | --- | --- | --- |
| B1 | CI/CD | 无 → GitHub Actions 跑 `pytest`+`ruff`+前端 `tsc/build` | P0 |
| B2 | 容器化 | 无 → Dockerfile + compose + 就绪/存活探针 | P1 |
| B3 | 数据库 | sqlite+`create_all` → 可切 Postgres + Alembic 迁移；档案表与会话表解耦 | P1 |
| B4 | API 安全 | 全开放 → 鉴权 + 限流 + CORS + 输入上限 + 成本上限 | P1 |
| B5 | 韧性 | 易卡死 → LLM 超时 + 重试退避 + 备用模型 fallback + 熔断/降级 | P0 |

### C. 领域深度（命理特有）

- **C1. 补全确定性工具 · P1**：大运/流年推算、合婚/合盘确定性打分、择日。让运势/关系分析有据可依而非 LLM 自由发挥。
- **C2. 知识接地 RAG · P2**：命理规则库 / 经典文献检索增强，降低解读幻觉。
- **C3. 报告引用 · P2**：解读结论标注其确定性依据（已部分有 `deterministic_basis`，可强化为强校验）。

### D. 锦上添花
- D1 档案管理 UI（编辑/删除）· D2 报告导出（PDF/图片）· D3 移动端适配 · D4 高风险问题的结构化免责/转人工 · D5 `ARCHITECTURE.md` / `CONTRIBUTING.md`。

---

## 3. 重点新增：Agent Harness + Loop 架构

### 3.1 动机

当前的「执行流」是**隐式**的：依赖 SDK 的 handoff agent loop + `max_turns` + 工具去重。这能跑，但：
- 不可控（弱模型空转/卡死，只能靠兜底）；
- 不可验证（生成完即返回，无质量/事实闸门）；
- 不可观测/不可回归（无 trace、无评测）。

近期主流做法是引入**显式的 Agent Harness（执行框架）**：在 LLM 之外，由确定性代码控制「计划 → 行动 → 观察 → 验证 → 修订」的循环（Loop），把质量、成本、安全做成框架级保证，而不是寄希望于模型自觉。

### 3.2 目标架构（在不抛弃 SDK 的前提下增强）

新增 `app/harness/` 层，包裹现有 `Runner`：

```
app/harness/
  loop.py          # 主控制循环：Plan → Act → Observe → Verify → Revise → Finalize
  stages.py        # 各阶段实现（规划、执行、校验、修订）
  policy.py        # 预算/轮次/超时/重试/降级策略（含 fallback 模型）
  verifiers.py     # 事实一致性 + 护栏校验（联动 A3/A6）
  budget.py        # token/成本/时间预算与统计（联动 A2）
  trace.py         # 统一埋点（联动 A2）
```

### 3.3 控制循环（Harness Loop）

```
输入
 └─> [Plan]    主控产出计划：需要哪些专家/工具、门禁是否通过
 └─> [Act]     执行：handoff + 确定性工具（复用现有 tools/agents）
 └─> [Observe] 收集工具结果、结构化输出
 └─> [Verify]  护栏 + 事实一致性校验（报告四柱/五行 == 工具结果？含 boundary？无确定性承诺？）
       ├─ 通过 ─> [Finalize] 渲染 Markdown，落档案，返回
       └─ 失败 ─> [Revise]  把校验失败点作为反馈回灌，重生成（最多 N 次）
 全程受 [Policy]：max_turns / token 预算 / 墙钟超时 / 重试退避 / 备用模型 约束，并写入 [Trace]
```

### 3.4 Loop 模式库（按需启用）

1. **Reason–Act–Observe（基线）**：现有 SDK 循环，纳入 harness 统一观测与限额。
2. **Verify–Revise（最高价值）**：生成后校验事实/护栏，不合格则带批注重试 ≤N 次。直接落地 A3 + A6。
3. **Plan-first**：先出执行计划再路由，降低错误 handoff。
4. **LLM-as-Judge 质量闸**：对报告打分，低于阈值触发修订（可选，成本换质量）。
5. **Fan-out–Synthesize**：复杂合盘按维度并行分析再综合（多人/多维场景）。
6. **Loop-until（收敛/预算）**：在「补全到 N 条建议」「预算耗尽前持续深挖」等场景循环，带显式上限与 `log` 防静默截断。
7. **Background / Scheduled Loop（前瞻）**：定时主动任务（如流年提醒），cron 触发同一 harness。

### 3.5 与现有代码的衔接

- 复用：`WenjiaRunContext`（扩展承载 budget/trace）、`stream_runner` 的 flow 事件（增加 verify/revise 阶段事件，前端流程卡片天然可展示）、`output_format`（finalize 阶段）、`profile_store`（finalize 落档）。
- 改造：`runner.py` / `stream_runner.py` 从「直接调 Runner」改为「调 harness.loop」，Runner 成为 Act 阶段的内部实现。
- 前端：运行流弹窗新增「校验 / 修订」节点，把质量闸做可视化。

### 3.6 验收标准
- 注入错误命盘的报告会被 Verify 拦下并在 ≤N 次修订内纠正；
- 每次 run 的 trace 含各阶段耗时、token、是否触发修订/降级；
- 弱模型或 provider 故障下：超时 → 重试 → fallback → 优雅降级，不卡死、不死循环；
- 所有 Loop 模式均有显式上限，超限有日志与 trace，无静默截断。

---

## 4. 优先级与路线图

| 阶段 | 内容 | 关联需求 |
| --- | --- | --- |
| **P0 / 第一期：可信地基** | Evals 框架、Tracing、Guardrails、事实校验、韧性（超时/重试/fallback）、CI | A1 A2 A3 A6 B5 B1 |
| **P0–P1 / 第二期：Harness + Loop** | 落地 `app/harness/`，先做 Plan-first + Verify–Revise，串起护栏与事实校验 | 第 3 节 + A3 A6 |
| **P1 / 第三期：产品化** | 逐字流式、上下文/记忆管理、Docker、Postgres+迁移、API 安全 | A4 A5 B2 B3 B4 |
| **P1–P2 / 第四期：领域深度** | 大运流年/合婚/择日工具、RAG 知识库、报告引用强化 | C1 C2 C3 |
| **P2 / 第五期：体验** | 档案管理 UI、报告导出、移动端、文档 | D1–D5 |

---

## 5. 风险与取舍
- **成本**：Verify–Revise / LLM-judge / RAG 会增加 token 成本——做成可配置开关，按场景启用。
- **延迟**：多阶段循环增加延迟——用并行（fan-out）与缓存（已有工具去重）缓解；逐字流式改善体感。
- **复杂度**：harness 不应重复造 SDK 的轮子——只在 SDK 之上补「计划/校验/修订/预算/观测」，Act 仍交给 SDK。
- **模型依赖**：弱模型（如当前 SiliconFlow 配置）是质量与稳定性的主要变量——评测体系正是为量化「换模型」的影响而建。
