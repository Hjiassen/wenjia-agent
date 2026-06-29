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

## 运行 Web Demo

先在 `.env` 填写 `OPENAI_API_KEY`，然后运行：

```powershell
poetry run uvicorn examples.web.app:app --reload --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

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
poetry run python -m compileall app examples tests
```

## PR 前检查

```powershell
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python -m compileall app examples tests
```

## Prompt 模板

Prompt 模板位于 `app/prompts`。

规则：

- 不在 Agent 定义中硬编码长 prompt。
- 使用 `app.prompts.load_prompt` 加载 prompt 文件。
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
