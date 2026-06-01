# Harness Engineering on GitHub Copilot: Design Principles

## 什么是 Harness Engineering（定义）

Harness Engineering（驾驭工程）是一种系统化的 AI 协作方法论。与简单的 prompt engineering 不同，它通过**结构化的规则、角色和工作流**来约束和引导 AI agent 的行为，使其在团队工程实践中稳定、可预测、安全地运作。

核心理念：不是写一个好 prompt，而是搭建一套**驾驭系统**（harness），让 AI 在明确的边界内发挥最大价值。

## 为什么 Harness > Prompt Engineering（对比）

| 维度 | Prompt Engineering | Harness Engineering |
|------|-------------------|-------------------|
| 作用范围 | 单次对话 | 整个项目生命周期 |
| 可复用性 | 低，依赖个人经验 | 高，团队共享配置文件 |
| 一致性 | 每次对话可能不同 | 规则层保证行为一致 |
| 安全性 | 靠人记住规则 | 系统级 guardrails 强制执行 |
| 协作性 | 单人使用 | 多 agent 协作，角色分明 |
| 可审计性 | 无 | 规则和流程可 review、可版本控制 |

**结论**：Prompt Engineering 是技巧，Harness Engineering 是工程体系。

## 三层 Harness 模型（3-Layer Harness Model）

```
┌─────────────────────────────────────────┐
│  Workflow Layer （工作流层）               │
│  .github/prompts/*.prompt.md            │
│  定义具体任务流程：Think→Plan→Build→Test  │
├─────────────────────────────────────────┤
│  Role Layer （角色层）                    │
│  .github/agents/*.agent.md              │
│  定义专家角色：architect, reviewer, etc.  │
├─────────────────────────────────────────┤
│  Rule Layer （规则层）                    │
│  .github/copilot-instructions.md        │
│  全局规则：代码风格、安全约束、质量标准     │
└─────────────────────────────────────────┘
```

**自下而上生效**：Rule Layer 是基础，所有 agent 和 workflow 都必须遵守。Role Layer 定义专家视角。Workflow Layer 编排具体任务。

### Rule Layer — `copilot-instructions.md`
- 项目级全局规则，对所有 Copilot 交互生效
- 包含：语言规范、安全约束、代码质量标准、协作协议

### Role Layer — Custom Agents (`.agent.md`)
- 每个 agent 文件定义一个专家角色
- 明确角色边界、专业领域、可用工具
- 示例：`architect.agent.md`、`security-reviewer.agent.md`

### Workflow Layer — Prompt Files (`.prompt.md`)
- 定义可复用的任务模板
- 编排多步骤流程
- 可引用特定 agent 来执行子任务

## 多角色 Agent 哲学

参考 gstack 的设计理念：**每个角色 = 一个专家视角**。

| 角色 | 职责 | 类比 |
|------|------|------|
| Architect | 系统设计、技术选型、架构决策 | 技术总监 |
| Developer | 功能实现、代码编写 | 高级工程师 |
| Reviewer | 代码审查、质量把关 | Tech Lead |
| Security Reviewer | 安全审计、漏洞检测 | 安全工程师 |
| Tester | 测试策略、用例编写 | QA 工程师 |

**关键原则**：
- 角色之间有明确边界，不越权
- 通过 `@mention` 机制在角色间传递任务
- 每个角色带有自己的 system prompt 和工具权限

## Sprint 流程：Think → Plan → Build → Review → Test → Ship

改编自 gstack 的开发流程，适配 GitHub Copilot 环境：

1. **Think（思考）** — 理解需求，分析约束，识别风险
2. **Plan（规划）** — 设计方案，拆解任务，确定实现路径
3. **Build（构建）** — 编写代码，遵循 Rule Layer 的所有规范
4. **Review（审查）** — 调用 reviewer agent 进行代码审查
5. **Test（测试）** — 运行测试，确保覆盖率，验证 edge cases
6. **Ship（交付）** — 提交 PR，附完整描述，等待人工确认

每一步都有对应的 prompt file 可以驱动自动化执行。

## Safety & Guardrails 哲学

安全不是附加功能，而是**系统架构的一部分**。

### 不可违反的规则（Hard Guardrails）
- ❌ 永远不删除文件（除非用户明确确认）
- ❌ 永远不 force-push 到 main/master
- ❌ 永远不修改 `.env` 或 credential 文件
- ❌ 永远不在 API response 中暴露 stack trace

### 必须执行的规则（Mandatory Actions）
- ✅ 提交前必须运行测试
- ✅ 所有用户输入必须做 sanitization
- ✅ 错误信息必须可操作（说明问题 + 给出修复方向）

### 设计原则
- **Fail-safe by default**：不确定时选择更安全的行为
- **Explicit > Implicit**：宁可多问一句，不要默认执行危险操作
- **Audit trail**：所有重要决策可追溯

## 对比：gstack (Claude Code) vs 本 Workshop (GitHub Copilot)

> **两个标杆，不是一个。** 本 Workshop 刻意对照*两个*参考 harness，让学员看到 harness 设计是**一条光谱、而非单一答案**：**gstack**（面向 Claude Code 的多角色工程流程）与 **ECC**（一个开源 agent 系统，其特色是*跨 harness 可移植*与*每个 agent 自带防御基线*）。gstack 展示"工程流程"风格；ECC 展示"可移植 + 自我防御的 agent"风格；本 Workshop 把两者都适配到 GitHub Copilot。

| 维度 | gstack (Claude Code) | ECC（开源 agent 系统） | 本 Workshop (GitHub Copilot) |
|------|---------------------|------------------------|----------------------------|
| AI 引擎 | Claude (Anthropic) | 模型无关 | GPT-4o / Claude (via Copilot) |
| 配置文件 | `CLAUDE.md` + `ETHOS.md` | 每 agent 定义 | `copilot-instructions.md` |
| 角色定义 | SubAgents in CLAUDE.md | 每 agent 文件 | `.agent.md` 文件 |
| 工作流 | Bash scripts + prompts | 跨 harness 工作流 | `.prompt.md` 文件 |
| 核心原则 | Boil the Lake, Search Before Building, User Sovereignty | PURPOSE 传递、每 agent 防御基线、token 预算硬约束 | Completeness First, Search Before Building, User Sovereignty |
| 跨 harness 可移植 | 低（Claude 专属） | **高（设计目标）** | 中（Copilot 生态） |
| 每 agent 注入防御 | 未强调 | **内置于每个 agent** | Lab 2 (Part D-2) 新增 |
| IDE 集成 | Terminal-based (CLI) | 随宿主而定 | VS Code 原生集成 |
| 适用场景 | 全栈开发、复杂重构 | 可移植的多 agent 系统 | 日常开发、团队协作、Code Review |
| 企业适用性 | 小团队/个人 | 需要宿主可移植的团队 | 企业级（GitHub 生态集成） |

**核心共识**：三者都认同——AI agent 需要结构化约束才能在工程实践中可靠运作。差异在于*风格*：gstack 偏工程流程，ECC 偏可移植 + 内置防御，本 Workshop 把两者所长都适配进 Copilot 生态。

> 注：引用 ECC 仅取其有文档记载的工程实践；不以其 star 数 / 流行度作为可信度依据（三方数字打架）。只看它的代码与文档来判断。

## 企业团队最佳实践

### 1. 版本控制你的 Harness
- 将 `copilot-instructions.md`、`.agent.md`、`.prompt.md` 全部纳入 Git
- 通过 PR review 来修改规则，而非随意编辑

### 2. 渐进式采用
- 第一周：只配置 `copilot-instructions.md`（Rule Layer）
- 第二周：添加 2-3 个核心 agent（Role Layer）
- 第三周：编写常用 workflow prompt（Workflow Layer）

### 3. 团队对齐
- 定期 review 和更新 harness 配置
- 新成员 onboarding 时包含 harness 培训
- 建立 harness 模板库供团队复用

### 4. 度量与改进
- 追踪 AI 辅助代码的 bug 率
- 收集团队对 agent 行为的反馈
- 定期迭代 guardrails 和 quality standards

### 5. 安全合规
- 敏感项目使用更严格的 guardrails
- 定期审计 agent 的行为日志
- 确保 AI 生成的代码通过安全扫描

---

> *"好的工具需要好的驾驭方式。Harness Engineering 就是让 AI 成为可靠队友的工程方法。"*
