# 需求报告

## 项目定位

`wenjia-agent` 是一个开源中文命理 Agent 项目，面向希望在产品中嵌入命理对话、排盘、分析、起名、关系分析能力的开发者。

项目只提供 Agent 层和确定性命理核心，不包含账号、支付、订单、会员、运营后台等业务后端。

## 用户与使用者

- 开源开发者：希望复用八字工具、Agent 编排、prompt 模板。
- 产品团队：希望把命理 Agent 嵌入自己的 App、网站、小程序或客服系统。
- 内容团队：希望基于确定性命盘生成结构稳定、边界清楚的命理解读。

## 核心需求

1. 支持用自然语言收集出生资料。
2. 支持公历/农历输入和闰月参数。
3. 支持出生地省市查询与经度兜底。
4. 支持确定性八字排盘与真太阳时。
5. 支持五行、十神、纳音、神煞、空亡、命宫等字段输出。
6. 支持命格分析、关系合盘、起名建议等专门 Agent。
7. 支持 `SQLAlchemySession` 保存 Agent 会话记忆。
8. 支持 prompt 文件化管理，方便社区协作。
9. 支持 Pydantic 结构化输出，便于上层产品集成。
10. 支持 Apache-2.0 许可证下的开源使用。

## 功能范围

### 已纳入

- 主控 Agent 路由
- ProfileAgent 排盘
- FortuneAgent 命格报告
- RelationshipAgent 关系分析
- NamingAgent 起名建议
- MysticToolsAgent 工具查询与字段解释
- 八字确定性工具
- 命盘上下文构建工具
- CLI 示例
- 单元测试与开发文档

### 不纳入

- 用户账号
- 登录认证
- 支付
- 订单
- 会员
- 运营后台
- 多租户权限
- 商业计费

## 验收标准

- `poetry check` 通过。
- `poetry run pytest` 通过。
- `poetry run ruff check . --no-cache` 通过。
- `poetry run python -m compileall app examples tests` 通过。
- 所有 Agent 能正常导入。
- 所有 prompt 模板存在且处于 active 状态。
- 八字相关结论必须来自工具，不由模型自行推算。
