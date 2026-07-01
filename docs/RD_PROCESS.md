# 研发流程

## 分支策略

- `main` 保持可运行。
- 功能开发使用 `feature/<topic>`。
- 修复使用 `fix/<topic>`。
- 文档使用 `docs/<topic>`。

## 开发步骤

1. 明确需求和边界，确认是否属于纯 Agent 模块。
2. 更新或新增 schema。
3. 实现 adapter、context builder 或 tool。
4. 实现 Agent 和 prompt。
5. 添加单元测试。
6. 更新 README 或 docs。
7. 运行本地质量检查。

## 质量门禁

每次合并前运行：

```powershell
poetry check
poetry run ruff check . --no-cache
poetry run pytest
poetry run python -m compileall wenjia_agent examples tests
```

## Prompt 评审

Prompt 修改需要检查：

- 是否要求工具计算八字。
- 是否避免确定性承诺。
- 是否明确文化娱乐边界。
- 是否覆盖缺失资料追问。
- 是否适配对应 output schema。

## 发布流程

1. 更新版本号。
2. 更新 changelog 或 release notes。
3. 运行质量门禁。
4. 打 tag。
5. 发布源码包或 GitHub Release。

## Issue 标签建议

- `agent`
- `tool`
- `prompt`
- `schema`
- `docs`
- `bug`
- `good first issue`
- `help wanted`
