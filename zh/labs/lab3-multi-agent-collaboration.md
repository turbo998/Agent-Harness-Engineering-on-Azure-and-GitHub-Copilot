# 实验 3：Multi-Agent 协作

## 实验目标

体验多个 Agent 各司其职、协作完成一个完整交付：

```
Developer Agent → 实现功能
Test Engineer Agent → 补充测试
Security Reviewer Agent → 安全审查
Doc Writer Agent → 生成文档
```

完成后，学员应能够：
1. 理解 Multi-Agent 协作的核心模式：**任务拆解 → 角色分工 → 并行/串行执行 → 结果汇总**
2. 使用 custom agent + agent handoff 实现多角色协作
3. 理解 Mission Control 的概念和使用时机

## 实验时长
20 分钟

## Multi-Agent 协作的三种模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **串行 handoff** | Agent A 完成后把结果交给 Agent B | 功能开发 → 测试 → review |
| **并行执行** | 多个 Agent 同时处理不同子任务 | 不同模块、不同文件、互不依赖 |
| **Mission Control** | 一个协调者管理多个 Agent 的任务分配和进度 | 复杂项目、需要跨仓库协调 |

本实验聚焦 **串行 handoff** 和 **并行执行**，这是最实用也最容易在 workshop 中落地的模式。

---

## 实验准备

确保你已经完成实验 2，即 `lab-starter` 目录下已有：
- `.github/copilot-instructions.md`
- `.github/agents/test-engineer.md`

### 新增 Agent 定义

#### Security Reviewer Agent

创建文件：`lab-starter/.github/agents/security-reviewer.md`

```markdown
---
name: security-reviewer
description: Agent specialized in security review for API code
---

# Security Reviewer Agent

You are a security specialist reviewing Node.js Express API code.

## Your responsibilities
- Review code for common security vulnerabilities
- Check input validation completeness
- Identify potential injection attacks
- Review error handling (no stack trace leaks)
- Check for missing authentication/authorization (if applicable)

## Review checklist
For each endpoint, verify:
1. Input sanitization
2. Proper HTTP status codes for errors
3. No sensitive data in responses
4. Rate limiting considerations (flag if missing)
5. CORS/header security (flag if missing)

## Rules
- NEVER modify code directly
- Output findings as a structured security review report
- Classify findings as: CRITICAL / WARNING / INFO
- For each finding, provide: location, issue, recommendation

## Output format
```
## Security Review Report
### CRITICAL
- [location] Issue: ... → Recommendation: ...
### WARNING
- [location] Issue: ... → Recommendation: ...
### INFO
- [location] Issue: ... → Recommendation: ...
```
```

#### Doc Writer Agent

创建文件：`lab-starter/.github/agents/doc-writer.md`

```markdown
---
name: doc-writer
description: Agent for generating API documentation and changelogs
---

# Doc Writer Agent

You are a technical documentation specialist.

## Your responsibilities
- Generate clear API documentation for endpoints
- Write changelogs for recent changes
- Create usage examples with curl/PowerShell commands
- Keep documentation concise and developer-friendly

## Rules
- NEVER modify source code or test files
- Documentation must include: endpoint, method, parameters, response format, example
- Use markdown format
- Include both success and error response examples
- Write in English

## Output files
- API docs: `docs/api.md`
- Changelog: `docs/CHANGELOG.md`
```

---

## 实验步骤

### Step 1：Developer Agent 实现功能 — 5 min

使用 Agent 模式（默认 agent），给出一个新功能需求：

**Prompt：**
```text
Add a DELETE /tickets/:id endpoint to this project.

Requirements:
- Delete a ticket by ID
- Return 204 on success
- Return 404 if ticket not found
- Add the deleteTicket function in ticketStore.js
- Add the route in app.js
- Run tests when finished
```

**等待 Agent 完成实现。**

---

### Step 2：Test Engineer Agent 补充测试 — 5 min

切换到 `@test-engineer` agent：

**Prompt：**
```text
@test-engineer Review the new DELETE /tickets/:id feature and ensure comprehensive test coverage.

Check for:
- Successful deletion
- Deleting non-existent ticket
- Deleting already-deleted ticket (double delete)
- Verifying ticket is gone after deletion via listTickets
- Run all tests when done
```

**你应该观察到：**
- test-engineer 只修改测试文件
- 添加了多个测试用例覆盖正常和异常场景
- 自动运行 npm test

**学习点：**
这就是 handoff：Developer Agent 做完开发，Test Engineer Agent 接手做测试。两个 Agent 各有专长和约束。

---

### Step 3：Security Reviewer Agent 安全审查 — 5 min

切换到 `@security-reviewer` agent：

**Prompt：**
```text
@security-reviewer Perform a security review of the entire ticket service API.
Focus especially on the new DELETE /tickets/:id endpoint, but also review all existing endpoints.
```

**你应该观察到：**
- Agent 输出结构化的 security review report
- 分类为 CRITICAL / WARNING / INFO
- 可能会发现：
  - DELETE 没有认证机制（WARNING）
  - 某些输入缺少长度限制（WARNING）
  - 没有 rate limiting（INFO）

**学习点：**
Security Reviewer Agent 不改代码，只做审查。这种"只读型 Agent"在企业环境中特别有价值：审查权和修改权分离。

---

### Step 4：Doc Writer Agent 生成文档 — 3 min

切换到 `@doc-writer` agent：

**Prompt：**
```text
@doc-writer Generate complete API documentation for this ticket service.
Include all endpoints (existing + new DELETE endpoint).
Also generate a changelog entry for the DELETE feature.
```

**你应该观察到：**
- 生成了 `docs/api.md`，包含所有端点的文档
- 生成了 `docs/CHANGELOG.md`
- 文档中包含 curl 示例

---

### Step 5：复盘 Multi-Agent 协作 — 2 min

回顾刚才的流程：

```
┌─────────────┐    ┌─────────────────┐    ┌───────────────────┐    ┌──────────────┐
│  Developer   │ →  │  Test Engineer   │ →  │ Security Reviewer  │ →  │  Doc Writer   │
│  实现功能    │    │  补充测试        │    │  安全审查          │    │  生成文档     │
│  改代码+跑测试│    │  只改测试文件    │    │  只输出报告        │    │  只写文档     │
└─────────────┘    └─────────────────┘    └───────────────────┘    └──────────────┘
```

| Agent | 职责 | 权限边界 |
|-------|------|---------|
| Developer | 实现功能 | 可改所有代码，可跑命令 |
| Test Engineer | 补测试 | 只改测试文件 |
| Security Reviewer | 审查 | 只读，不改代码 |
| Doc Writer | 文档 | 只写 docs/ 目录 |

**讲师话术：**
> Multi-Agent 协作的关键不是"用更多 Agent"，而是"每个 Agent 有清晰的职责和权限边界"。
> 这和真实团队的协作模式完全一致：开发、测试、安全、文档各有分工。
> 在实际落地中，你还可以通过 Mission Control 来管理多个 Agent 的进度，让它们在不同 branch / repo 上并行工作。

---

## 高级讨论：跨运行时 Agent 协作

### 超越单一框架

在本 Lab 中，所有 Agent 都运行在同一个 GitHub Copilot 框架内。但在生产环境中，企业通常有 **多种 Agent 运行时** 共存：

```
┌──────────────────────────────────────────────────────────┐
│                     消息平台                              │
│              (Slack / Teams / 飞书 / 微信)                │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Copilot Agent │  │ Hermes Agent │  │ 自定义 Agent  │  │
│  │ (代码任务)    │  │ (运维任务)   │  │ (数据任务)    │  │
│  │ GitHub 原生   │  │ 多工具      │  │ Python        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            ▼                             │
│                    LiteLLM Gateway                       │
│                  (统一模型访问)                           │
└──────────────────────────────────────────────────────────┘
```

### 为什么需要多种运行时？

| 原因 | 示例 |
|------|------|
| **能力互补** | Copilot 擅长代码；Hermes 擅长运维/聊天；专用 Agent 处理数据 |
| **团队自主** | A 团队用 Copilot，B 团队自研了 Agent — 两者应该共存 |
| **渐进式采纳** | 先用 Copilot 做代码，逐步加入运维/数据 Agent |
| **供应商多元化** | 避免锁定在单一 Agent 框架 |

### 协作方式

跨运行时的 Agent 不直接调用彼此的 API。它们通过 **共享制品** 协作：

1. **共享代码库** — Copilot Agent 写代码，Hermes Agent 负责部署，两者读取同一份 SOUL.md
2. **共享消息频道** — 所有 Agent 发到同一个 Slack/Teams 频道，由人类协调
3. **共享模型网关** — LiteLLM 提供统一的访问、预算和可观测性
4. **共享 Harness 文件** — SOUL.md、copilot-instructions.md 和 Agent 定义跨运行时通用

### 部署路径

| 路径 | 具体形态 |
|------|---------|
| **Azure Container Apps** | 每个 Agent 运行时 = 独立的 Container App，共享 VNet，共享 LiteLLM |
| **VM** | 每个 Agent 运行时 = 独立的 Docker 容器或进程，共享宿主机，共享 LiteLLM |
| **混合模式** | Copilot 运行在 GitHub 云端，Hermes 运行在 Azure VM，两者都访问 Azure OpenAI |

### 讨论问题

1. 在你的组织中，哪些任务适合用 **非 Copilot** 的 Agent（如运维自动化、数据管线、客户支持）？
2. 如何确保不同运行时的 Agent 保持一致的行为？（提示：共享 SOUL.md + 共享模型网关）
3. 跨运行时协作的最小可行方案是什么？（答案：共享 Slack 频道 + 共享 LiteLLM 端点）

---

## 进阶讨论：Mission Control 与 Coding Agent

### 什么是 Mission Control？

Mission Control 是 GitHub 提供的 Multi-Agent 编排界面，支持：
- 同时运行多个 Coding Agent（cloud agent）
- 在不同 repo / branch 上并行执行
- 监控进度、查看产出、中途调整方向
- 每个 Agent 自动创建 PR

### 典型场景

```
Mission Control
├── Agent 1: repo-frontend → 实现 UI 组件
├── Agent 2: repo-backend → 实现 API 端点
├── Agent 3: repo-docs → 更新文档
└── Agent 4: repo-infra → 更新 CI/CD 配置
```

### 什么时候从 Local Multi-Agent 升级到 Mission Control？

| 场景 | 推荐方式 |
|------|---------|
| 单仓库、小任务 | Local Agent + Custom Agent handoff（本实验） |
| 单仓库、复杂任务 | Local Agent + Coding Agent delegation |
| 多仓库、并行任务 | Mission Control |
| CI/CD 驱动的自动化 | Coding Agent + GitHub Actions |

---

## 延伸阅读：和 Claude Code Agent Teams 的对比

2026-05 Anthropic 在 Claude Code 推出了实验特性 **Agent Teams**（队友间可同步通信、共享任务列表、Plan 审批 + hook 硬约束）。从 GitHub Copilot 视角看，它与 Copilot 的 Custom Agents / Coding Agent / Mission Control 是同一类工程化路线下的不同产品形态。

四档场景选型快速参考：

| 任务画像 | 推荐方案 |
|---------|---------|
| 单仓库、可拆分子任务 | Copilot Custom Agents handoff（本实验） |
| 单仓库、需要「同事讨论」 | Claude Code Agent Teams |
| 跨仓库、跨 PR 并行 | Copilot Coding Agent + Mission Control / Agent HQ |
| 几百 sub-agent 大规模分解 | 云端 Swarm（Kimi K2.6 / 自建） |

完整对比（概念映射、成本/限额、合作伙伴话术）：[`zh/docs/copilot-vs-claude-code-agent-teams.md`](../docs/copilot-vs-claude-code-agent-teams.md)

---

## 实验完成标准

- [ ] Developer Agent 完成了 DELETE 端点实现
- [ ] Test Engineer Agent 补充了测试（只改测试文件）
- [ ] Security Reviewer Agent 输出了安全审查报告
- [ ] Doc Writer Agent 生成了 API 文档
- [ ] 理解了 Multi-Agent 的串行 handoff 模式
- [ ] 了解了 Mission Control 的适用场景

---

## 常见问题

**Q: 如果某个 Agent 的输出不符合预期怎么办？**
A: 可以给它更明确的指令重试，或者在 copilot-instructions.md 中补充约束。

**Q: 可以让多个 Agent 同时运行吗？**
A: 在 VS Code 的本地 Agent 模式中，通常是串行的。如果需要真正的并行，可以使用 Coding Agent（cloud）+ Mission Control。

**Q: Custom Agent 的定义会影响其他协作者吗？**
A: 是的，`.github/agents/` 下的文件会跟随仓库，所有协作者都可以使用这些 agent。
