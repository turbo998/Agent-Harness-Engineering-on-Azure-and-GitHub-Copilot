# 实验 1：AI-DLC 全生命周期闭环

## 实验目标

用 GitHub Copilot 走完一个完整的 **AI-Driven Development Life Cycle**：

```
需求理解 → 规划 → 实现 → 测试 → Review → PR 描述
```

完成后，学员应能够理解：GHCP 不只是写代码，而是可以参与开发全生命周期。

## 实验时长
20 分钟

## 实验场景

**需求**：为 ticket service 新增一个 `GET /tickets/summary` 端点

- 返回按 `status` 和 `priority` 分别聚合的统计信息
- 补充对应测试
- 生成 PR 描述

## 实验步骤

### Phase 1：需求理解（Ask）— 3 min

切到 **Ask** 模式。

**Prompt：**
```text
I need to add a GET /tickets/summary endpoint to this project.
Before I start, help me understand:
1. What is the current data model and API surface?
2. What existing patterns should I follow?
3. Are there any potential edge cases for a summary endpoint?
```

**你应该观察到：**
- Copilot 分析了 ticketStore.js 的数据结构
- 识别出现有的路由风格（Express、JSON 响应）
- 提到了 edge case（空数据、未知 status 值等）

**学习点：**
在 AI-DLC 中，第一步永远不是写代码，而是让 AI 帮你理解上下文和识别风险。

---

### Phase 2：规划（Plan）— 3 min

切到 **Plan** 模式。

**Prompt：**
```text
Create a detailed implementation plan for GET /tickets/summary.
Include:
- Which files to modify
- Function signatures
- Test cases to add
- Verification steps
```

**你应该观察到：**
Plan 输出一个结构化的步骤列表，通常包括：
1. 在 ticketStore.js 新增 `getSummary()` 函数
2. 在 app.js 新增 `GET /tickets/summary` 路由
3. 在测试文件新增至少 2-3 个测试用例
4. 运行 `npm test` 验证

**学习点：**
Plan 的输出可以看作一份"AI 生成的技术方案"，团队可以先 review 方案再决定是否执行。

---

### Phase 3：实现（Agent）— 5 min

切到 **Agent** 模式。

**Prompt：**
```text
Implement the /tickets/summary endpoint based on the plan.

Requirements:
- Add a getSummary() function in ticketStore.js
- Add GET /tickets/summary route in app.js
- Return JSON with countByStatus and countByPriority
- Add tests covering: normal case, empty data, single-status data
- Run tests when finished
```

**你应该观察到：**
- Agent 逐步修改多个文件
- 自动运行 `npm test`
- 如果测试失败，Agent 会尝试修复

**学习点：**
Agent 执行的不是"一次性生成"，而是一个 loop：实现 → 验证 → 修正 → 再验证。

---

### Phase 4：测试验证 — 3 min

在终端确认：

```powershell
npm test
```

启动服务并手动验证：

```powershell
npm start
# 另开终端
curl http://localhost:3000/tickets/summary
```

**期待输出示例：**
```json
{
  "countByStatus": { "open": 1, "in_progress": 1, "resolved": 1 },
  "countByPriority": { "high": 1, "medium": 1, "low": 1 }
}
```

---

### Phase 5：Review + PR 描述（Ask）— 3 min

切回 **Ask** 模式。

**Prompt 1 — Code Review：**
```text
Review the changes I just made for the /tickets/summary endpoint.
Check for:
- Security issues
- Performance concerns
- Missing edge cases
- Code style consistency
```

**Prompt 2 — PR 描述：**
```text
Draft a pull request description for the /tickets/summary feature.
Include: problem statement, solution summary, test coverage, and how to verify.
```

**学习点：**
AI-DLC 的最后一步不是"代码写完就提交"，而是让 AI 帮你做 self-review 和文档化。

---

### Phase 6：复盘 — 3 min

回顾刚才走过的完整 AI-DLC：

| 阶段 | GHCP 模式 | 产出 |
|------|----------|------|
| 需求理解 | Ask | 上下文分析、风险识别 |
| 规划 | Plan | 结构化实现方案 |
| 实现 | Agent | 跨文件代码修改 |
| 测试 | Agent + Terminal | 自动运行测试 |
| Review | Ask | 代码审查意见 |
| 文档化 | Ask | PR 描述 |

**讲师收尾话术：**
> 这就是 AI-DLC：不是让 AI 替你写代码，而是让 AI 参与开发全生命周期的每一步。
> 关键是：你始终在控制方向，AI 在提供加速。

---

## 实验完成标准

- [ ] 用 Ask 理解了需求上下文
- [ ] 用 Plan 产出了结构化方案
- [ ] 用 Agent 完成了跨文件实现
- [ ] 测试通过且 API 可调用
- [ ] 用 Ask 完成了 code review
- [ ] 生成了 PR 描述

---

## 常见问题

**Q: Agent 修改的文件和 Plan 不一致怎么办？**
A: 这是正常的。Agent 在执行中可能发现更优路径。重要的是检查最终结果是否满足需求。

**Q: 测试失败了怎么办？**
A: 让 Agent 继续修复，或缩小范围重试。AI-DLC 的核心就是"迭代"。
