# Contributing

感谢参与 `wenjia-agent`。

## 项目边界

- 本仓库保持纯 Agent 模块。
- 不添加账号、认证、支付、订单、会员或运营后台。
- 八字和历法逻辑放在 `app/core`。
- Agent-facing adapter 和 schema 放在 `app/domain`。
- OpenAI Agents SDK function tools 放在 `app/tools`。
- Prompt 模板放在 `app/prompts`。

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
poetry run python -m compileall app examples tests
```

## Pull Request Checklist

- 说明变更内容和原因。
- 关联 issue 或 proposal。
- 代码变更需要补测试。
- 行为变化需要更新文档。
- 结构化输出使用 Pydantic schema。
- 不在工具函数里硬编码 prompt。
- 不在 Python Agent 文件里硬编码长 instructions，使用 `app/prompts`。
- 不引入非 Agent 业务模块。

## 新工具贡献

新增工具需要包含：

- Pydantic schema 或明确的类型参数。
- `app/tools` 中的 function tool wrapper。
- 不带装饰器的内部函数，方便测试。
- `tests` 下的单元测试。
- 面向用户的工具需要补充 `docs` 文档。

确定性工具不得调用 LLM。
