# wenjia-agent Web Demo

This example provides a lightweight Chinese browser chat UI for `wenjia-agent`.
It supports multi-turn chat, local conversation history, and preset recommended
questions. Agent context is keyed by `session_id`, while the visible chat history
is stored in the browser's `localStorage`.

## Run

Windows PowerShell:

```powershell
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

Linux:

```bash
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Environment

Copy `.env.example` to `.env` and configure:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Static web UI |
| `GET` | `/health` | Health check |
| `POST` | `/api/chat` | Run one Agent turn |
| `GET` | `/docs` | FastAPI-generated API docs |
