# 实验 2：Harness Engineering — 驯服你的 Agent

## 实验目标

学会通过 **copilot-instructions.md**、**custom agent**、**prompt file** 来约束和定制 Agent 的行为。

完成后，学员应能够：
1. 编写 `copilot-instructions.md` 定义全局规则
2. 创建 custom agent 专注于特定任务
3. 使用 prompt file 实现可复用的任务模板
4. 理解"Harness Engineering"：**Agent 的能力由 harness 决定，而不是由 prompt 碰运气**

## 实验时长
15 分钟

## 什么是 Harness Engineering？

传统：写一个长 prompt → 祈祷 AI 按你的意思来
Harness Engineering：**用结构化的配置文件系统性地约束 Agent 的行为边界、输出风格、工具使用方式**

GHCP 提供的 harness 机制包括：

| 机制 | 文件 | 作用 |
|------|------|------|
| Custom Instructions | `.github/copilot-instructions.md` | 全局行为约束 |
| Custom Agent | `.github/agents/*.md` | 专用角色定义 |
| Prompt File | `.github/prompts/*.prompt.md` | 可复用的任务模板 |
| MCP Server | `.vscode/mcp.json` | 扩展 Agent 可用的工具 |

---

## 实验步骤

### Step 1：创建 copilot-instructions.md — 5 min

在 `lab-starter` 目录下创建文件：

```
lab-starter/.github/copilot-instructions.md
```

内容：

```markdown
# Project Conventions

## Language & Style
- All code must use JavaScript (CommonJS, no TypeScript).
- Follow the existing Express.js patterns in this project.
- Use `node:test` and `node:assert/strict` for tests (no Jest, no Mocha).

## Code Rules
- Every new API endpoint MUST have corresponding test cases.
- Input validation errors MUST return HTTP 400 with a JSON `{ error: "..." }` body.
- Do NOT install new npm packages without explicit approval.
- Keep functions small (< 30 lines).

## Git & PR
- Commit messages must follow: `<type>: <description>` (e.g., `feat: add summary endpoint`).
- PR descriptions must include: Problem, Solution, Test Coverage, Verification Steps.

## Security
- Never expose stack traces in API responses.
- Sanitize all user inputs before processing.
```

**讲师讲解：**
> 这个文件就像是给 Agent 的"员工手册"。不管你接下来用 Ask、Plan 还是 Agent，Copilot 都会参考这些规则。

---

### Step 2：创建 Custom Agent — 5 min

在 `lab-starter` 目录下创建文件：

```
lab-starter/.github/agents/test-engineer.md
```

内容：

```markdown
---
name: test-engineer
description: Specialized agent for writing and improving test coverage
---

# Test Engineer Agent

You are a test engineering specialist for this Node.js project.

## Your responsibilities
- Write comprehensive test cases using `node:test` and `node:assert/strict`
- Ensure edge cases are covered (empty input, invalid data, boundary values)
- Run tests after writing them and fix failures
- Report test coverage gaps

## Rules
- NEVER modify production code (only test files)
- Always run `npm test` after writing tests
- Group related tests using `test.describe()`
- Include at least one positive case, one negative case, and one edge case per function

## Output format
After completing tests, provide a summary:
1. Tests added
2. Tests passing/failing
3. Coverage gaps remaining
```

**验证方式：**
在 VS Code Chat 中切换到 Agent 模式，从 agent 下拉列表中选择 `test-engineer`。

**Prompt：**
```text
@test-engineer Check the current test coverage for ticketStore.js and add any missing test cases.
```

**你应该观察到：**
- Agent 只修改测试文件，不动 production code
- 遵循 node:test 风格
- 自动运行 npm test

**学习点：**
Custom Agent = 专用角色。不是"什么都会"的通用 Agent，而是"只做一件事且做得好"的专家。

---

### Step 3：创建 Prompt File — 3 min

创建文件：

```
lab-starter/.github/prompts/add-endpoint.prompt.md
```

内容：

```markdown
---
name: add-endpoint
description: Template for adding a new API endpoint
mode: agent
---

Add a new API endpoint to this Express.js project.

## Endpoint: {{ endpoint_path }}
## Method: {{ http_method }}
## Description: {{ description }}

## Implementation steps:
1. Add business logic in `src/ticketStore.js`
2. Add route in `src/app.js`
3. Add tests in `tests/ticketStore.test.js`
4. Run `npm test` to verify

## Constraints:
- Follow existing code patterns
- Return proper HTTP status codes
- Include input validation where needed
- All tests must pass before declaring done
```

**使用方式：**
在 VS Code Chat 中使用 prompt file：

```text
/add-endpoint endpoint_path=/tickets/stats http_method=GET description="Return ticket statistics including average resolution time"
```

**学习点：**
Prompt file = 可复用的任务模板。团队可以把常见任务标准化，减少每次手写 prompt 的不确定性。

---

### Step 4：体验约束效果 — 2 min

现在用 Agent 模式发一个"违反规则"的请求，观察 harness 的约束效果：

**Prompt：**
```text
Install lodash and use it to rewrite the listTickets function with _.filter()
```

**你应该观察到：**
如果 copilot-instructions.md 生效，Agent 应该：
- 提醒你"不能安装新 npm 包"
- 或者拒绝这个请求
- 或者用原生 JS 替代

**讲师话术：**
> 这就是 Harness Engineering 的价值：不是靠"prompt 写得好"来控制 Agent，而是靠**结构化的配置文件**来系统性地约束行为边界。
> 对企业客户来说，这意味着可以在组织层面定义 Agent 的行为规范。

---

## 实验完成标准

- [ ] 创建了 `.github/copilot-instructions.md` 并理解其作用
- [ ] 创建了 `.github/agents/test-engineer.md` custom agent
- [ ] 用 `@test-engineer` 调用了专用 agent
- [ ] 创建了 `.github/prompts/add-endpoint.prompt.md`
- [ ] 理解了 harness 对 Agent 行为的约束效果

---

## 关键概念对比

| 方式 | 适用场景 | 持久性 |
|------|---------|--------|
| 写好 prompt | 一次性任务 | 用完就没了 |
| copilot-instructions.md | 全局项目规范 | 跟随仓库，所有协作者共享 |
| custom agent | 专用角色 | 跟随仓库，可被团队复用 |
| prompt file | 可复用任务模板 | 跟随仓库，参数化使用 |

**一句话总结：** Harness Engineering = 把"好的 prompt 习惯"变成"可版本控制的团队资产"。
