# Deployment Guide

This guide covers the public deployment options included with `wenjia-agent`.
The live demo is available at:

https://www.jiajiahome.top/

## Environment

Create `.env` from `.env.example` and set at least:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_AGENT_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
WENJIA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://www.jiajiahome.top
WENJIA_OPENAI_SDK_TRACING=false
```

For production, use a persistent database path and keep traces in a controlled
directory:

```env
WENJIA_SESSION_DB_URL=sqlite+aiosqlite:///./wenjia_agent_sessions.db
WENJIA_TRACE_DIR=logs/traces
```

Do not commit `.env`, local SQLite databases, or trace logs.

## Local Web App

Run backend and frontend as two processes:

```bash
poetry run uvicorn apps.web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd apps/web/frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Ubuntu Preview Runner

If the server already has Python, Poetry, Node, and the repository checkout,
use the lightweight runner:

```bash
bash scripts/deploy_ubuntu.sh restart
bash scripts/deploy_ubuntu.sh status
```

By default it starts:

- Backend: `0.0.0.0:8000`
- Frontend Vite preview: `0.0.0.0:5173`
- PID files: `.run/`
- Logs: `logs/`

Use hot reload only when needed:

```bash
FRONTEND_MODE=dev bash scripts/deploy_ubuntu.sh restart
```

## Static Nginx Deployment

For a production-style single-domain deployment, build the frontend, publish it
under `/var/www`, and let Nginx serve static assets while proxying `/api` and
`/health` to FastAPI.

```bash
bash scripts/deploy_static_nginx.sh deploy
```

Install the example Nginx config after replacing `example.com`:

```bash
sudo cp docs/deploy/nginx.example.conf /etc/nginx/conf.d/wenjia-agent.conf
sudo nginx -t
sudo systemctl reload nginx
```

Common overrides:

```bash
WEB_ROOT=/var/www/wenjia-agent BACKEND_PORT=8000 bash scripts/deploy_static_nginx.sh deploy
NGINX_CONF_SOURCE=docs/deploy/nginx.example.conf bash scripts/deploy_static_nginx.sh nginx
```

The public example intentionally avoids machine-specific domains, certificate
paths, and private config. Keep personal Nginx files outside Git or under
ignored local paths such as `docs/vibe_coding/`.

## Docker Compose

Docker Compose builds two services:

- `backend`: FastAPI + `wenjia_agent` runtime on port 8000 inside the network.
- `frontend`: Nginx serving the React build and proxying `/api` + `/health`.

Prepare `.env`, then run:

```bash
docker compose up --build
```

Open http://localhost:8080.

The compose stack stores runtime data in named volumes:

- `wenjia-data`: SQLite session/profile data.
- `wenjia-logs`: local trace logs.

Stop the stack:

```bash
docker compose down
```

Remove volumes only when you intentionally want to delete local sessions and
traces:

```bash
docker compose down -v
```

## Production Notes

- Put the app behind HTTPS before sharing it publicly.
- Keep `OPENAI_API_KEY` server-side only; never expose it to the browser.
- Configure `WENJIA_CORS_ORIGINS` to the exact frontend origins you serve.
- Add authentication, rate limits, abuse monitoring, and retention policy for
  public deployments.
- Treat local traces and SQLite data as sensitive user data.
