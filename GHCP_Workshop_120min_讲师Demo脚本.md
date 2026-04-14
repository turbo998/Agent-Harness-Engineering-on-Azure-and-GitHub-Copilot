# GitHub Copilot 客户技术工作坊 Demo 脚本

## 1. Demo 目标

在 20 分钟内让客户技术团队看到 GitHub Copilot 从 **IDE 辅助** 走向 **Agent 模式执行** 的完整路径：

1. **Ask**：快速理解代码库与需求
2. **Plan**：生成结构化实现方案
3. **Agent**：执行跨文件修改、补测试、验证结果
4. **讲师讲解**：解释审批、自治、handoff 的使用时机

Demo 项目使用本目录下的 `lab-starter`。

---

## 2. Demo 时间分配

| 环节 | 时长 | 目标 |
| --- | ---: | --- |
| 场景引入 | 2 min | 说明业务场景与当前代码状态 |
| Ask 模式 | 4 min | 让 Copilot 快速解释代码与识别缺口 |
| Plan 模式 | 4 min | 生成变更计划与执行步骤 |
| Agent 模式 | 8 min | 自动实现功能、补测试、运行验证 |
| 总结 | 2 min | 强调适用场景与治理边界 |

---

## 2.5 PPT 新增页讲法（Harness Engineering）

在 Demo 前后，可插入 3–5 分钟解释：

### 页 1：Harness Engineering 不是 magic prompt

建议讲法：

> 很多人第一次接触 Agent，会把注意力放在“prompt 怎么写更厉害”。
> 但在真实团队里，稳定性往往不来自一句更花哨的话，而来自 Agent 的运行环境设计。
>
> 也就是：
> - 有没有项目级 instructions
> - 有没有角色边界
> - 有没有高频任务模板
> - 有没有 tests / lint / CI 给 agent 自动纠偏

一句话总结：

> Prompt engineering 提高一次对话质量；Harness engineering 提高整个团队长期使用 Agent 的成功率。

### 页 2：参考案例页怎么讲

可引用这些热门参考：

- `github/awesome-copilot`
- `walkinglabs/awesome-harness-engineering`
- Copilot Customization Handbook

建议讲法：

> 这些高关注度资源都在说明一件事：
> Agent 落地正在从“个人技巧”走向“工程资产”。
>
> 企业客户真正关心的不是“AI 会不会写代码”，
> 而是“AI 能不能在一个可治理、可验证、可复用的环境里稳定干活”。

---

## 3. Demo 场景

### 3.1 背景

团队维护一个客户支持工单服务，现在需要快速做一个小增强：

1. 增加 `GET /tickets/summary`
2. 返回按 `status` 和 `priority` 聚合的统计结果
3. 补充测试

### 3.2 为什么选这个场景

- 代码量小，便于现场理解
- 涉及跨文件修改，适合展示 agent 的价值
- 可同时展示：
  - 代码解释
  - 规划能力
  - 自动改代码
  - 自动补测试
  - 验证结果

---

## 4. Demo 前准备

### 4.1 本地准备

在 `lab-starter` 目录执行：

```powershell
npm install
npm test
```

### 4.2 VS Code 准备

- 打开 `lab-starter`
- 确认已登录 GitHub Copilot
- 确认 Chat 中可以切换到 **Ask / Plan / Agent**
- 如果组织启用了 agent permissions，可准备展示：
  - Default Approvals
  - Bypass Approvals
  - Autopilot（如租户可用则提及，不强依赖现场演示）

### 4.3 备用方案

如果现场网络或权限不稳定：

1. 直接展示已准备好的 prompt 和预期输出
2. 手动切到已完成版本或用讲师口述 diff
3. 强调 Demo 的重点是工作流，不是打字速度

---

## 5. Demo 详细脚本

## Step 1：用 Ask 模式理解代码库

### 讲师话术

“先不要急着改代码。对技术团队来说，第一步往往是快速理解已有系统，再决定怎么改。”

### 建议 Prompt

```text
Explain this project as if I just joined the team.
Focus on the API surface, the data model, and any obvious gaps or TODOs.
```

### 期待结果

Copilot 应能识别：

- 这是一个 Express API
- 当前支持 health、ticket list、create、status update
- `ticketStore.js` 有两个 workshop TODO：
  - priority 过滤
  - createTicket 校验

### 讲解重点

- Ask 适合快速获取上下文
- 不改代码，适合“理解”“解释”“调研”

---

## Step 2：切到 Plan 模式生成实现计划

### 讲师话术

“接下来把需求交给 Plan，让它先产出执行步骤，而不是直接动手。”

### 建议 Prompt

```text
Create a plan to add a GET /tickets/summary endpoint.
The endpoint should return counts by status and by priority.
Include tests and keep the existing coding style.
```

### 期待结果

Plan 应包含：

1. 查看现有 store 和 app 结构
2. 在 store 中新增 summary 逻辑
3. 在 app 中新增 route
4. 为新逻辑添加测试
5. 运行测试验证

### 讲解重点

- Plan 适合“先想清楚再执行”
- 对客户技术团队很重要，因为这能帮助他们控制 agent 的范围和预期

---

## Step 3：切到 Agent 模式执行任务

### 讲师话术

“现在把一个定义清楚的任务交给 Agent。重点不是它会不会写代码，而是它能否自己跨文件推进，并在需要时使用工具完成闭环。”

### 建议 Prompt

```text
Implement the /tickets/summary endpoint for this project.

Requirements:
- Add a GET /tickets/summary route
- Return counts grouped by status and by priority
- Keep the response JSON easy to read
- Add or update tests
- Run the tests when finished
```

### 期待行为

Agent 可能会：

- 阅读 `src/app.js`
- 阅读 `src/ticketStore.js`
- 修改一个或多个文件
- 更新 `tests/ticketStore.test.js`
- 运行 `npm test`

### 讲解重点

- 这就是 agent loop：理解任务、分解、执行、纠错、验证
- 可顺便解释 approval 流程：
  - 为什么有些环境要人工批准
  - 什么时候可以给更高自治

---

## Step 4：讲权限与治理

在 agent 执行过程中或执行后补充说明：

- **Default Approvals**：更适合刚开始试点或高风险仓库
- **Bypass Approvals**：适合边界清晰、希望更快推进的任务
- **Autopilot**：适合标准化任务，但要搭配清晰 guardrails

### 推荐讲法

“真正落地时，关键不是让 agent ‘能不能改’，而是让团队决定它‘在什么边界内可以改’。”

---

## Step 5：验证结果

在终端运行：

```powershell
npm test
```

如需补充运行 API：

```powershell
npm start
```

另开终端验证：

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/tickets/summary"
```

### 期待输出

输出中应包含：

- 按状态的统计
- 按优先级的统计

---

## 6. Demo 讲师提示

### 6.1 需要强调的价值点

1. GitHub Copilot 不只是补全代码，而是能参与完整开发流
2. Ask / Plan / Agent 不是替代关系，而是不同阶段的模式
3. Agent 价值在于：
   - 跨文件修改
   - 能跑命令
   - 能回看结果并修正
4. 技术团队仍然保留边界控制与审批权

### 6.2 避免踩坑

- 不要让现场 Demo 的需求过大
- 不要同时塞入太多新概念
- 不要依赖网络临场发挥
- 不要把重点放在“生成速度”，要放在“工作流闭环”

---

## 7. Demo 收尾总结

可用如下收束话术：

> 对技术团队来说，最有价值的不是让 Copilot 帮你少写几行代码，而是让它开始承担一部分完整任务：先理解，再规划，再执行，再验证。  
> 这也是今天 workshop 后半段实验要让大家亲手体验的部分。
