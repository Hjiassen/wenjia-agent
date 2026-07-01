# wenjia-agent Web App

[简体中文](README.md) | [English](README.en.md)

`wenjia-agent` 的免登录浏览器聊天应用，采用**彻底的前后端分离**架构：

- **backend/** — 只提供 API 的 FastAPI 服务（JSON + SSE）。原样复用
  `wenjia_agent/runtime/*` 的 Agent 内核，不返回任何 HTML。
- **frontend/** — 独立的 React + TypeScript（Vite）SPA，基于
  **[Ant Design X](https://x.ant.design/)**（Bubble / Sender / Conversations /
  ThoughtChain）构建，把 Agent 运行过程渲染成带思考链的实时对话。

Agent 记忆以 `session_id` 为键；可见的对话历史保存在浏览器的 `localStorage`。

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

## 配置

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `WENJIA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的浏览器来源（逗号分隔）。 |
| `OPENAI_API_KEY` | — | 实际调用 Agent 所需。 |
| `WENJIA_SESSION_DB_URL` | `sqlite+aiosqlite:///./wenjia_agent_sessions.db` | 会话/档案存储。 |

## 接口（仅 API）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查。 |
| `POST` | `/api/chat` | 运行一轮 Agent（非流式）。 |
| `POST` | `/api/chat/stream` | 流式返回 Agent 流程事件（SSE）+ 最终输出。 |
| `GET` | `/api/profiles/{session_id}` | 某会话归档的人物档案。 |
| `GET` | `/docs` | FastAPI 自动生成的接口文档。 |
