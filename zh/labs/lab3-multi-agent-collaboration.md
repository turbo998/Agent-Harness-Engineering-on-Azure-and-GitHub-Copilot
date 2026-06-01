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

## Step 6：A/B 练习 —— 传 PURPOSE vs. 只传 task —— 5 min

> **借鉴 ECC 的跨 harness 架构：** 上游 agent 应该把"这件事为什么重要"（PURPOSE）传给下游 agent，而不只是"做什么"。这个练习让学员亲身感受差异。

把**同一个**交接跑两遍，对比下游产出。

**变体 A —— 只传 task。** 只带任务交给 security-reviewer：

```text
@security-reviewer Review the /users endpoint.
```

**变体 B —— task + PURPOSE。** 同样的任务，但带上目的：

```text
@security-reviewer Review the /users endpoint.
PURPOSE: 这个 API 将面向一个合作伙伴的 SaaS offer、暴露给不可信的公网客户端，
因此「会进入未来 SQL 层的输入」和「响应中的任何数据泄露」是最高优先级风险。
```

**观察并对比：**
- 变体 B 是否优先盯住这个语境下真正要紧的风险（注入抵达 SQL 层、响应数据泄露），而不是套一份通用清单？
- 变体 B 的报告是否读起来更*对齐*真实目标？
- 对 doc-writer 做同样的 A/B：知道受众（"集成该 SaaS offer 的合作伙伴开发者"）是否改变了文档的深度与示例？

**讲解金句：**
> task 告诉下游 agent *做什么*；PURPOSE 告诉它*在任务模糊时该为什么而优化*。大多数"agent 技术上做了、但没抓住重点"的失败，是缺 PURPOSE 的失败，而非能力的失败。在多 agent 流水线里，要把 PURPOSE 沿链路往下传，而不只是传 task。

**坑：** PURPOSE 不是扩大范围的许可证。下游 agent 仍应遵守自己的权限边界（security-reviewer 依然只写报告）—— PURPOSE 是*在边界内*磨锐判断力，而非移除边界。

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
