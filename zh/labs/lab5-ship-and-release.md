# Lab 5: 端到端发布流程 — 从设计到上线

⏱ **预计时间**: 25 分钟 | **难度**: 高级

## 🎯 学习目标

完成本实验后，你将能够：

1. 体验完整的 Think → Plan → Build → Review → Test → Ship 开发周期
2. 在每个阶段使用对应的专业 Agent 和 Prompt
3. 理解 gstack 风格的工程流程如何用 Copilot 落地
4. 独立运用多 Agent 协作完成一个功能从设计到发布的全流程

## 📋 前置条件

- 已完成 Lab 1–4
- 已配置所有 Agent：`@product-reviewer`、`@architect`、`@test-engineer`、`@release-engineer`、`@code-reviewer`
- 已配置所有 Prompt：`design-feature.prompt`、`code-review.prompt`、`ship-release.prompt`
- `lab-starter/` 项目可正常运行且 `npm test` 通过

---

## 📖 场景

产品经理提出需求：**支持更新工单状态**。需要新增 `PATCH /tickets/:id` 端点，允许更新工单的 `status` 字段（`open` → `in-progress` → `closed`）。

你将以完整的工程流程交付这个功能。

---

## Phase 1: Think — 需求评估与架构设计（5 分钟）

### 1.1 产品评审

```
@product-reviewer 我们计划新增 PATCH /tickets/:id 端点，允许更新工单状态。
状态流转规则：open → in-progress → closed，不允许回退。
请从产品角度评审这个需求，指出潜在问题和改进建议。
```

**✅ 预期反馈**：
- 是否需要支持 `closed → reopen`？
- 状态变更是否需要备注/原因？
- 是否需要通知相关人员？
- 权限控制 — 谁可以变更状态？

> [!NOTE]
> **讲师提示**：强调 Think 阶段的价值 — 在写代码之前发现需求层面的问题，成本最低。让学员简单记录产品建议，但本 Lab 聚焦工程流程，不需要全部采纳。

### 1.2 架构设计

```
@architect 请为 PATCH /tickets/:id 端点设计技术方案。
需求：更新工单 status 字段，状态流转 open → in-progress → closed，不可回退。
当前项目是 Express + 内存存储的结构。请给出 API 设计、数据校验、错误处理的方案。
```

**✅ 预期输出**：
- API 契约：`PATCH /tickets/:id` body: `{ "status": "in-progress" }`
- 状态机验证逻辑
- 错误码设计：400（无效状态）、404（工单不存在）、409（状态流转非法）
- 建议的文件修改清单

---

## Phase 2: Build — 生成实现计划并编码（5 分钟）

### 2.1 生成实现计划

```
/design-feature PATCH /tickets/:id 端点
需求：更新工单状态，状态流转 open → in-progress → closed，不可回退。
参考架构方案：[粘贴 Phase 1.2 的关键输出]
```

**✅ 预期输出**：结构化的实现步骤清单，包含需要修改的文件和具体变更。

### 2.2 使用 Agent Mode 实现

在 Copilot Chat 中切换到 **Agent Mode**（点击模式切换按钮），然后输入：

```
请根据以下设计方案，在 lab-starter 项目中实现 PATCH /tickets/:id 端点：

1. 在 src/routes/tickets.js 中添加 PATCH 路由
2. 验证 :id 参数格式
3. 验证请求体包含 status 字段
4. 实现状态流转校验（open → in-progress → closed，不可回退）
5. 返回更新后的 ticket 对象
6. 处理 404（ticket 不存在）和 409（非法状态转换）
```

**验证实现**：

```bash
# 创建一个测试工单
curl -X POST http://localhost:3000/tickets \
  -H "Content-Type: application/json" \
  -d '{"title": "Test ticket", "status": "open"}'

# 更新状态
curl -X PATCH http://localhost:3000/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "in-progress"}'

# 应返回 409 — 不允许回退
curl -X PATCH http://localhost:3000/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "open"}'
```

> [!TIP]
> **讲师提示**：Agent Mode 会自动创建/修改文件。提醒学员查看 Copilot 做了哪些文件变更，不要盲目接受。

---

## Phase 3: Review — 多角色代码审查（5 分钟）

### 3.1 运行统一审查

```
/code-review 请审查我刚实现的 PATCH /tickets/:id 端点
```

### 3.2 修复发现的问题

根据审查报告，逐一修复发现的问题。常见发现：

- 输入验证不够严格
- 缺少请求速率限制
- 错误消息泄露内部信息

```
@code-reviewer 我已根据审查意见做了以下修改：[描述修改]。请确认是否已解决所有问题。
```

> [!NOTE]
> **讲师提示**：真实工作中 Review 可能需要多轮。本 Lab 限时，修复 1-2 个关键问题即可。

---

## Phase 4: Test — 生成并运行测试（5 分钟）

### 4.1 生成测试用例

```
@test-engineer 请为 PATCH /tickets/:id 端点生成全面的测试用例，覆盖：
1. 正常状态流转（open → in-progress → closed）
2. 非法回退（closed → open）
3. 不存在的 ticket（404）
4. 无效的 status 值（400）
5. 缺少 status 字段（400）
6. 无效的 id 格式
```

**✅ 预期输出**：一组完整的测试代码（Jest/Supertest），覆盖正常路径和异常路径。

### 4.2 运行测试

将生成的测试代码保存到 `lab-starter/tests/tickets-patch.test.js`，然后运行：

```bash
cd lab-starter
npm test
```

**预期结果**：所有测试通过。如果有失败，根据错误信息修复实现代码。

> [!TIP]
> **讲师提示**：如果时间紧张，学员可以只运行 Agent 生成的测试，不手动调整。重点是体验流程，不是 100% 通过率。

---

## Phase 5: Ship — 准备发布（5 分钟）

### 5.1 运行发布流程

```
/ship-release 准备发布 PATCH /tickets/:id 功能
版本：从当前版本做一个 minor 版本升级
变更摘要：新增工单状态更新端点，支持 open → in-progress → closed 状态流转
```

**或者使用 Agent**：

```
@release-engineer 请为以下功能变更准备发布：
- 新增 PATCH /tickets/:id 端点
- 支持工单状态流转：open → in-progress → closed
- 请完成：版本号升级、CHANGELOG 更新、发布说明
```

**✅ 预期输出**：

1. **package.json** 版本号升级（如 `1.0.0` → `1.1.0`）
2. **CHANGELOG.md** 新增条目：

```markdown
## [1.1.0] - 2025-XX-XX

### Added
- PATCH /tickets/:id endpoint for updating ticket status
- Status transition validation: open → in-progress → closed
- Input validation and error handling (400, 404, 409)
```

3. 发布检查清单：测试通过 ✅、审查完成 ✅、文档更新 ✅

### 5.2 最终验证

```bash
# 确认版本号
node -e "console.log(require('./package.json').version)"

# 确认测试通过
npm test

# 确认 CHANGELOG 已更新
head -20 CHANGELOG.md
```

> [!NOTE]
> **讲师提示**：在真实项目中，Ship 阶段还包括 CI/CD 流水线、staging 环境验证等。本 Lab 简化为本地操作，重点是理解流程。

---

## 🤔 反思与讨论（2 分钟）

### 回顾完整流程

```
Think    →  Plan   →  Build  →  Review  →  Test  →  Ship
  │           │         │          │         │        │
  ▼           ▼         ▼          ▼         ▼        ▼
product   architect   Copilot   code-review  test   release
reviewer              Agent      .prompt    engineer engineer
```

### 讨论问题

1. **流程价值**：哪个阶段发现的问题对你来说最"意外"？
2. **效率对比**：如果没有 AI Agent 辅助，完成同样的流程需要多久？
3. **质量门禁**：在你的团队中，哪些阶段最容易被跳过？AI 如何帮助确保流程完整？
4. **定制化**：你会为自己的项目调整哪些 Agent 的行为规则？

---

## 📝 关键收获

| # | 收获 |
|---|------|
| 1 | 完整的工程流程是 Think → Plan → Build → Review → Test → Ship |
| 2 | 每个阶段都有对应的专业 Agent 或 Prompt 提供支持 |
| 3 | 在编码前投入的 Think 时间，能大幅减少后续返工 |
| 4 | 统一的 Prompt 文件（如 `code-review.prompt`、`ship-release.prompt`）将最佳实践固化为可复用流程 |
| 5 | AI 不替代工程流程，而是让每个环节更高效、更一致 |

---

## 🎓 Workshop 总结

恭喜你完成了全部 5 个 Lab！回顾你的学习路径：

| Lab | 主题 | 核心能力 |
|-----|------|----------|
| 1 | AI-DLC 全生命周期 | 理解 AI 在开发各阶段的应用 |
| 2 | Harness Engineering 三层架构 | 掌握 Rule / Role / Workflow 配置 |
| 3 | 多 Agent 串行协作 | 使用多个 Agent 接力完成任务 |
| 4 | 多角色联合代码审查 | 不同角色并行审查，全面覆盖 |
| **5** | **端到端发布流程** | **完整的 Think→Ship 工程闭环** |

**下一步行动**：回到你的真实项目，选择一个即将开发的功能，用今天学到的流程实践一次完整的 Think → Ship 周期。
