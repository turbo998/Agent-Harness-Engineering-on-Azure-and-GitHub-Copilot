# Workshop 升级完整计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 参考 gstack 多角色 Agent 体系，将现有 120 分钟 GitHub Copilot Workshop 升级为 180 分钟深度 Workshop，覆盖完整 Harness Engineering 实践。

**Architecture:** 保留现有 Lab 1-3 核心框架，新增 Agent 角色（从 3→10）、Prompt 模板（从 1→6）、新增 Lab 4-5、增强 copilot-instructions.md、更新议程/讲稿/README。所有新增内容基于现有 Node.js Express ticket-service 项目。

**关键设计决策：**
- gstack 是 Claude Code 生态 → 我们适配为 GitHub Copilot Agent Mode
- gstack 的 SKILL.md 模板系统 → 我们用 `.github/agents/` + `.github/prompts/`
- gstack 的 Bash preamble → 我们用 Markdown 指令 + copilot-instructions.md
- 保留中文为主语言，代码/配置用英文

---

## Phase 1: 新增 Agent 角色文件（参考 gstack 角色体系）

### Task 1: 创建 code-reviewer Agent
**参考**: gstack `/review` + 7 个 specialist reviewers
**文件**: `lab-starter/.github/agents/code-reviewer.md`
**角色**: Staff Engineer 级别的代码审查者，覆盖安全/性能/可维护性/测试完整性

### Task 2: 创建 architect Agent
**参考**: gstack `/plan-eng-review`
**文件**: `lab-starter/.github/agents/architect.md`
**角色**: 工程架构师，负责技术方案评审、架构图、数据流分析

### Task 3: 创建 investigator Agent
**参考**: gstack `/investigate`
**文件**: `lab-starter/.github/agents/investigator.md`
**角色**: 根因分析专家，系统化调试，不急于修复而是先彻底理解问题

### Task 4: 创建 release-engineer Agent
**参考**: gstack `/ship` + `/land-and-deploy`
**文件**: `lab-starter/.github/agents/release-engineer.md`
**角色**: 发布工程师，负责测试→审查→版本号→CHANGELOG→PR→部署验证

### Task 5: 创建 product-reviewer Agent
**参考**: gstack `/plan-ceo-review` + `/office-hours`
**文件**: `lab-starter/.github/agents/product-reviewer.md`
**角色**: 产品评审者，从用户价值/商业逻辑角度审视功能设计

### Task 6: 创建 performance-engineer Agent
**参考**: gstack `/benchmark`
**文件**: `lab-starter/.github/agents/performance-engineer.md`
**角色**: 性能工程师，负责性能基准测试/瓶颈分析/优化建议

### Task 7: 创建 red-team Agent
**参考**: gstack `review/specialists/red-team.md`
**文件**: `lab-starter/.github/agents/red-team.md`
**角色**: 对抗性测试者，站在攻击者角度找漏洞、边界情况、信任假设

---

## Phase 2: 新增 Prompt 模板文件

### Task 8: 创建 fix-bug Prompt
**参考**: gstack `/investigate` 工作流
**文件**: `lab-starter/.github/prompts/fix-bug.prompt.md`
**用途**: 标准化 Bug 修复流程（复现→根因→修复→测试→回归）

### Task 9: 创建 code-review Prompt
**参考**: gstack `/review` 14 步审查流程
**文件**: `lab-starter/.github/prompts/code-review.prompt.md`
**用途**: 代码审查清单模板

### Task 10: 创建 ship-release Prompt
**参考**: gstack `/ship` 16 步流程
**文件**: `lab-starter/.github/prompts/ship-release.prompt.md`
**用途**: 发布流程模板（测试→审查→版本→PR）

### Task 11: 创建 design-feature Prompt
**参考**: gstack `/design-consultation` + `/office-hours`
**文件**: `lab-starter/.github/prompts/design-feature.prompt.md`
**用途**: 功能设计模板（需求分析→方案设计→评审→实现计划）

### Task 12: 创建 investigate-issue Prompt
**参考**: gstack `/investigate`
**文件**: `lab-starter/.github/prompts/investigate-issue.prompt.md`
**用途**: 问题调查模板

---

## Phase 3: 增强 copilot-instructions.md

### Task 13: 升级 copilot-instructions.md
**参考**: gstack ETHOS.md 三大原则 + CLAUDE.md 开发规范
**文件**: `lab-starter/.github/copilot-instructions.md`
**改进**: 加入完整性原则、搜索优先、用户主权、安全护栏、代码风格规范

---

## Phase 4: 新增 Lab 实验

### Task 14: 编写 Lab 4 — 多角色代码审查
**文件**: `labs/lab4-multi-role-code-review.md`
**内容**: 学员使用 code-reviewer + security-reviewer + red-team 三角色联合审查
**时长**: 20 分钟
**参考**: gstack `/review` specialist army 模式

### Task 15: 编写 Lab 5 — 端到端发布流程
**文件**: `labs/lab5-ship-and-release.md`
**内容**: 从功能开发到发布的完整流程（architect→开发→review→test→release）
**时长**: 25 分钟
**参考**: gstack Think→Build→Review→Test→Ship 全流程

---

## Phase 5: 更新总览文档

### Task 16: 更新议程为 180 分钟版
**文件**: `AHE_Workshop_180min_升级版议程.md`

### Task 17: 编写新版讲师 Demo 脚本
**文件**: `AHE_Workshop_180min_讲师Demo脚本.md`

### Task 18: 编写新版客户讲稿
**文件**: `AHE_Workshop_180min_客户讲稿版.md`

### Task 19: 更新 README.md
**文件**: `README.md`

### Task 20: 创建 DESIGN.md 设计理念文档
**参考**: gstack ETHOS.md
**文件**: `docs/DESIGN.md`
**内容**: Harness Engineering on GitHub Copilot 的设计理念和最佳实践

---

## 文件清单汇总

### 新增文件（17 个）
**Agents（7 个）:**
- `lab-starter/.github/agents/code-reviewer.md`
- `lab-starter/.github/agents/architect.md`
- `lab-starter/.github/agents/investigator.md`
- `lab-starter/.github/agents/release-engineer.md`
- `lab-starter/.github/agents/product-reviewer.md`
- `lab-starter/.github/agents/performance-engineer.md`
- `lab-starter/.github/agents/red-team.md`

**Prompts（5 个）:**
- `lab-starter/.github/prompts/fix-bug.prompt.md`
- `lab-starter/.github/prompts/code-review.prompt.md`
- `lab-starter/.github/prompts/ship-release.prompt.md`
- `lab-starter/.github/prompts/design-feature.prompt.md`
- `lab-starter/.github/prompts/investigate-issue.prompt.md`

**Labs（2 个）:**
- `labs/lab4-multi-role-code-review.md`
- `labs/lab5-ship-and-release.md`

**文档（3 个）:**
- `AHE_Workshop_180min_升级版议程.md`
- `AHE_Workshop_180min_讲师Demo脚本.md`
- `AHE_Workshop_180min_客户讲稿版.md`
- `docs/DESIGN.md`

### 修改文件（2 个）
- `lab-starter/.github/copilot-instructions.md`
- `README.md`
