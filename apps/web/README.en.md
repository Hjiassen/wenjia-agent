# wenjia-agent Web App

[简体中文](README.md) | [English](README.en.md)

A login-free browser chat app for `wenjia-agent`, built as a **fully separated
front/back stack**:

- **backend/** — an API-only FastAPI service (JSON + SSE). It reuses the agent
  core in `app/runtime/*` unchanged and serves **no** HTML.
- **frontend/** — a standalone React + TypeScript (Vite) SPA built with
  **[Ant Design X](https://x.ant.design/)** (Bubble / Sender / Conversations /
  ThoughtChain), rendering the Agent run as a live chat with an inline
  thought-chain of the flow events.

Agent memory is keyed by `session_id`; the visible chat history lives in the
browser's `localStorage`.

## Run (two processes)

### 1. Backend (API on :8000)

Fill `OPENAI_API_KEY` in `.env` first.

```bash
poetry run uvicorn apps.web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend (dev server on :5173)

```bash
cd apps/web/frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` and `/health` to
the backend, so no extra CORS setup is needed in development.

## Production

Build the SPA and host the static output anywhere (nginx, a CDN, object storage):

```bash
cd apps/web/frontend
npm run build      # outputs apps/web/frontend/dist/
```

Serve `dist/` and make sure it can reach the backend — either put both behind one
reverse proxy (same origin) or allow the SPA origin via `WENJIA_CORS_ORIGINS`.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `WENJIA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins (comma-separated). |
| `OPENAI_API_KEY` | — | Required for live Agent runs. |
| `OPENAI_AGENT_MODEL` | `gpt-4.1-mini` | Lightweight routing, profile collection, and tool-query Agents. |
| `OPENAI_ANALYSIS_MODEL` | `gpt-4.1-mini` | Specialist analysis Agents for fortune, relationship, and naming. |
| `OPENAI_FALLBACK_MODEL` | empty | Backup model used when the primary model times out or errors; empty disables fallback. |
| `WENJIA_INPUT_GUARDRAILS_ENABLED` | `true` | Whether deterministic input guardrails are enabled. |
| `WENJIA_INPUT_MAX_CHARS` | `8000` | Maximum user input length per turn. |
| `WENJIA_LONG_TERM_MEMORY_ENABLED` | `true` | Whether cross-session memory keyed by browser `client_id` is enabled. |
| `WENJIA_LONG_TERM_MEMORY_MAX_ITEMS` | `8` | Maximum long-term memory items injected per turn. |
| `WENJIA_MODEL_TIMEOUT_SECONDS` | `90` | Timeout for one model run. |
| `WENJIA_TRACE_ENABLED` | `true` | Whether to write local JSONL run traces. |
| `WENJIA_TRACE_DIR` | `logs/traces` | Local trace output directory. |
| `WENJIA_SESSION_DB_URL` | `sqlite+aiosqlite:///./wenjia_agent_sessions.db` | Session/profile store. |

## Endpoints (API only)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check. |
| `POST` | `/api/chat` | Run one Agent turn (non-streaming). |
| `POST` | `/api/chat/stream` | Stream Agent flow events (SSE) + final output. |
| `GET` | `/api/profiles/{session_id}` | Person profiles archived for a session. |
| `GET` | `/docs` | FastAPI-generated API docs. |
