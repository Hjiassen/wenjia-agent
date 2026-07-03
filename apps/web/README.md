# wenjia-agent Web App

[简体中文](README.md) | [English](README.en.md)

`wenjia-agent` 的免登录浏览器聊天应用，采用**彻底的前后端分离**架构：

- **backend/** — 只提供 API 的 FastAPI 服务（JSON + SSE）。原样复用
  `wenjia_agent/runtime/*` 的 Agent 内核，不返回任何 HTML。
- **frontend/** — 独立的 React + TypeScript（Vite）SPA，基于
  **[Ant Design X](https://x.ant.design/)**（Bubble / Sender / Conversations /
  ThoughtChain）构建，把 Agent 运行过程渲染成带思考链的实时对话。

Agent 同会话记忆以 `session_id` 为键；跨会话长期记忆以浏览器 `client_id`
为键；可见的对话历史保存在浏览器的 `localStorage`。

## 运行（两个进程）

### 1. 后端（API，端口 8000）

先在 `.env` 填写 `OPENAI_API_KEY`。

```bash
poetry run uvicorn apps.web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 前端（开发服务器，端口 5173）

```bash
cd apps/web/frontend
npm install
npm run dev
```

打开 http://localhost:5173。Vite 开发服务器会把 `/api`、`/health` 代理到后端，
开发环境无需额外配置 CORS。

## 生产部署

构建 SPA，把静态产物托管到任意位置（nginx、CDN、对象存储）：

```bash
cd apps/web/frontend
npm run build      # 输出到 apps/web/frontend/dist/
```

托管 `dist/` 并确保它能访问到后端——要么把前后端放在同一个反向代理后（同源），
要么用 `WENJIA_CORS_ORIGINS` 放行前端来源。

如果 Ubuntu 服务器已经装好 Python / Poetry / Node，并且已经拉好仓库，可以用轻量脚本启动或重启服务。
脚本会拉取远端代码，然后用 pid/log 管理 FastAPI 后端和前端。默认前端使用 `npm run build`
和 `npm run preview`，远程访问会比 Vite dev server 快很多：

```bash
bash scripts/deploy_ubuntu.sh restart
```

常用命令：

```bash
bash scripts/deploy_ubuntu.sh start
bash scripts/deploy_ubuntu.sh stop
bash scripts/deploy_ubuntu.sh restart
bash scripts/deploy_ubuntu.sh status
```

默认后端监听 `0.0.0.0:8000`，前端监听 `0.0.0.0:5173`；pid 文件在 `.run/`，日志在 `logs/`。
如果需要热更新调试，可以改用开发模式：

```bash
FRONTEND_MODE=dev bash scripts/deploy_ubuntu.sh restart
```

## 配置

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `WENJIA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的浏览器来源（逗号分隔）。 |
| `OPENAI_API_KEY` | — | 实际调用 Agent 所需。 |
| `OPENAI_AGENT_MODEL` | `gpt-4.1-mini` | 主控路由、资料收集、工具查询等轻量 Agent。 |
| `OPENAI_ANALYSIS_MODEL` | `gpt-4.1-mini` | 命格、合盘、起名等正式分析 Agent。 |
| `OPENAI_FALLBACK_MODEL` | 空 | 主模型超时或异常时的备用模型；留空则禁用。 |
| `WENJIA_SESSION_HISTORY_LIMIT` | `40` | 每轮从同一 `session_id` 取回的最近会话消息条数；设为 `0` 或负数表示不限制。 |
| `WENJIA_INPUT_GUARDRAILS_ENABLED` | `true` | 是否启用输入护栏。 |
| `WENJIA_INPUT_MAX_CHARS` | `8000` | 单次用户输入最大长度。 |
| `WENJIA_LONG_TERM_MEMORY_ENABLED` | `true` | 是否启用基于浏览器 `client_id` 的跨会话长期记忆。 |
| `WENJIA_LONG_TERM_MEMORY_MAX_ITEMS` | `8` | 每轮按当前问题相关性注入模型的长期记忆条数上限。 |
| `WENJIA_MODEL_TIMEOUT_SECONDS` | `90` | 单次模型调用超时时间。 |
| `WENJIA_TRACE_ENABLED` | `true` | 是否写入本地 JSONL 运行追踪。 |
| `WENJIA_TRACE_DIR` | `logs/traces` | 本地 trace 输出目录。 |
| `WENJIA_SESSION_DB_URL` | `sqlite+aiosqlite:///./wenjia_agent_sessions.db` | 会话/档案存储。 |

## 接口（仅 API）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查。 |
| `POST` | `/api/chat` | 运行一轮 Agent（非流式）。 |
| `POST` | `/api/chat/stream` | 流式返回 Agent 流程事件（SSE）+ 最终输出。 |
| `GET` | `/api/profiles/{session_id}` | 某会话归档的人物档案。 |
| `GET` | `/api/memories?client_id=...` | 当前浏览器用户的长期记忆。 |
| `DELETE` | `/api/memories/{memory_id}?client_id=...` | 删除一条长期记忆。 |
| `GET` | `/docs` | FastAPI 自动生成的接口文档。 |
