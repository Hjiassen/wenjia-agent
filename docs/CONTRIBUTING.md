# Contributing

感谢参与 `wenjia-agent`。

提交 issue 或 PR 前，请先阅读根目录的 [行为准则](../CODE_OF_CONDUCT.md)。
如果你发现安全问题，请按 [安全政策](../SECURITY.md) 私下报告，不要在公开
issue 中贴 API key、私有出生资料、本地数据库或 trace 日志。

## 项目边界

- 本仓库保持纯 Agent 模块。
- 不添加账号、认证、支付、订单、会员或运营后台。
- 八字和历法逻辑放在 `wenjia_agent/core`。
- Agent-facing adapter 和 schema 放在 `wenjia_agent/domain`。
- OpenAI Agents SDK function tools 放在 `wenjia_agent/tools`。
- Prompt 模板放在 `wenjia_agent/prompts`。

## 开发环境

```powershell
poetry install --with dev
Copy-Item .env.example .env
```

提交 PR 前运行：

```powershell
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python -m compileall wenjia_agent examples tests
```

如果改动 Web 前端，还需要运行：

```powershell
cd apps\web\frontend
npm install
npm run build
```

如果改动 Docker 或部署文件，建议至少运行：

```powershell
docker compose config
bash scripts/deploy_ubuntu.sh status
```

## Issue 与讨论

- Bug report 请使用 GitHub issue 模板，并提供最小复现步骤。
- Feature request 请说明用户场景、建议方案和影响范围。
- 不要在 issue 中粘贴敏感环境变量、真实用户资料、SQLite 数据库或完整 trace。
- 命理内容属于文化娱乐和个人参考，讨论中避免把输出描述成专业医疗、法律、
  投资或心理建议。

## Pull Request Checklist

- 说明变更内容和原因。
- 关联 issue 或 proposal。
- 代码变更需要补测试。
- 行为变化需要更新文档。
- Prompt、tool、schema 或 API 行为变化需要在 PR 描述中明确说明。
- 结构化输出使用 Pydantic schema。
- 不在工具函数里硬编码 prompt。
- 不在 Python Agent 文件里硬编码长 instructions，使用 `wenjia_agent/prompts`。
- 不引入非 Agent 业务模块。

## 新工具贡献

新增工具需要包含：

- Pydantic schema 或明确的类型参数。
- `wenjia_agent/tools` 中的 function tool wrapper。
- 不带装饰器的内部函数，方便测试。
- `tests` 下的单元测试。
- 面向用户的工具需要补充 `docs` 文档。

确定性工具不得调用 LLM。
