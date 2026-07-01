# Development

本项目使用 Poetry 管理依赖和本地工作流。

## 安装

```powershell
cd D:\PythonProject\wenjia-agent
poetry install --with dev
Copy-Item .env.example .env
```

## 运行确定性八字 Demo

```powershell
poetry run python examples\cli_bazi.py
```

该 Demo 不需要 OpenAI API key。

## 运行 Agent Demo

先在 `.env` 填写 `OPENAI_API_KEY`，然后运行：

```powershell
poetry run python examples\cli_agent.py
```

## 运行 Web App

Web App 前后端分离：只提供 API 的 FastAPI 后端 + 独立的 React（Ant Design X）SPA，需分别启动两个进程。

后端（先在 `.env` 填写 `OPENAI_API_KEY`）：

```powershell
poetry run uvicorn apps.web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

前端（开发服务器 5173，自动代理 `/api`、`/health` 到后端）：

```bash
cd apps/web/frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173。生产构建：`npm run build`，产物在 `apps/web/frontend/dist/`。详见 [apps/web/README.md](../apps/web/README.md)。

## 测试

```powershell
poetry run pytest
```

## Lint

```powershell
poetry run ruff check . --no-cache
```

## 校验包配置

```powershell
poetry check
```

## 编译检查

```powershell
poetry run python -m compileall wenjia_agent examples tests
```

## PR 前检查

```powershell
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python -m compileall wenjia_agent examples tests
```

## Prompt 模板

Prompt 模板位于 `wenjia_agent/prompts`。

规则：

- 不在 Agent 定义中硬编码长 prompt。
- 使用 `wenjia_agent.prompts.load_prompt` 加载 prompt 文件。
- front matter 至少包含 `id`、`version`、`owner`、`status`。
- prompt 改变行为时，需要补充测试或示例。

## 新增依赖

运行时依赖：

```powershell
poetry add package-name
```

开发依赖：

```powershell
poetry add --group dev package-name
```

依赖应保持精简，并兼容 Apache-2.0 开源使用。
