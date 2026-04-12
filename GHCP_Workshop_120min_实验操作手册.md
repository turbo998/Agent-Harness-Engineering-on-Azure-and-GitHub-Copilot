# GitHub Copilot 客户技术工作坊实验操作手册

## 1. 实验目标

本实验面向客户技术团队，目标是在一个小型 Node.js 项目中，使用 GitHub Copilot 完成从 **理解代码**、**生成计划** 到 **Agent 模式修改代码并验证结果** 的完整闭环。

完成后，学员应能够：

1. 使用 **Ask** 模式快速理解项目结构
2. 使用 **Plan** 模式生成结构化实现方案
3. 使用 **Agent** 模式完成明确的小型开发任务
4. 理解何时使用 Ask、Plan、Agent
5. 理解审批与自治边界

---

## 2. 实验环境要求

### 2.1 必备软件

- Windows / macOS / Linux 任一桌面环境
- **Visual Studio Code**
- **Node.js 20+**
- **GitHub Copilot** 已开通并已登录

### 2.2 VS Code 建议准备

- 已安装 GitHub Copilot 扩展
- 已安装 GitHub Copilot Chat 扩展（如环境中为分离安装）
- Chat 面板中可切换 Ask / Plan / Agent

### 2.3 实验资料

实验目录：

`ghcp-workshop-120min\lab-starter`

---

## 3. 实验场景说明

你加入了一个客户支持平台项目。团队已有一个简化版 ticket API，但还缺少两项增强：

1. `GET /tickets` 支持按 `priority` 过滤
2. `POST /tickets` 增加输入校验

你的任务是借助 GitHub Copilot 完成这些增强，并补充测试。

---

## 4. 实验总流程

| 实验阶段 | 推荐时长 | 目标 |
| --- | ---: | --- |
| 环境准备 | 5 min | 打开项目并确认能运行 |
| Ask 模式理解项目 | 5 min | 了解代码结构与待办项 |
| Plan 模式生成方案 | 5 min | 明确改动步骤 |
| Agent 实验任务 A | 10 min | 实现 priority 过滤与测试 |
| Agent 实验任务 B | 10 min | 实现 POST 校验与测试 |
| 验证与复盘 | 5 min | 运行测试并总结模式使用场景 |

---

## 5. Step 0：打开实验项目

### 5.1 打开项目

在 VS Code 中打开：

`lab-starter`

### 5.2 打开终端

在 VS Code 终端执行：

```powershell
npm install
npm test
```

### 5.3 期待结果

你应该看到测试通过。

如果测试无法运行：

1. 检查 Node.js 是否安装
2. 检查 GitHub Copilot 登录状态
3. 检查当前打开的是否是 `lab-starter` 根目录

---

## 6. Step 1：用 Ask 模式理解项目

## 6.1 任务目标

先不要直接改代码，先理解项目：

- 有哪些 API
- 数据模型长什么样
- 哪些地方是待完成点

## 6.2 建议 Prompt

将 Chat 模式切到 **Ask**，输入：

```text
Explain this project in simple terms.
List the existing API routes, the ticket data shape, and any TODO items or obvious gaps.
```

## 6.3 你应该观察到什么

Copilot 应能说明：

- 项目是一个 Express API
- `src/app.js` 里有 health、list tickets、create ticket、update status
- `src/ticketStore.js` 是核心数据逻辑
- 有两个 workshop TODO：
  - 增加 priority 过滤
  - 增加 createTicket 校验

## 6.4 记录结论

请在本地记下两个问题：

1. `priority` 过滤尚未实现
2. `createTicket` 缺少输入校验

---

## 7. Step 2：用 Plan 模式生成实现计划

## 7.1 任务目标

在改代码前，先让 Copilot 给出清晰的实现步骤。

## 7.2 建议 Prompt

将 Chat 模式切到 **Plan**，输入：

```text
Create a plan for two changes in this project:
1. Add priority filtering to GET /tickets
2. Add validation for POST /tickets

Please include tests and keep the existing style.
```

## 7.3 你应该观察到什么

合理计划通常会包含：

1. 查看 `ticketStore.js` 中的 list 和 create 逻辑
2. 为 `listTickets` 增加 priority 条件
3. 为 `createTicket` 增加 title/customer/priority 校验
4. 新增或更新测试
5. 运行测试验证

## 7.4 学习点

- 当任务已经明确，但你还不希望它立刻改代码时，用 **Plan**
- 这能帮助你审视 scope，减少 agent 乱改

---

## 8. Step 3：Agent 实验任务 A - 增加 priority 过滤

## 8.1 任务说明

你要让 `GET /tickets` 支持：

`/tickets?priority=high`

## 8.2 推荐 Prompt

切到 **Agent** 模式，输入：

```text
Implement priority filtering for this project.

Requirements:
- Update the ticket listing logic so GET /tickets can filter by priority
- Keep the existing status filter behavior
- Add or update tests
- Run the tests when finished
```

## 8.3 执行时你需要观察什么

Agent 可能会：

- 先读 `src/ticketStore.js`
- 再读 `tests/ticketStore.test.js`
- 修改代码
- 运行 `npm test`

如你的环境需要审批，请按界面提示批准工具调用。

## 8.4 完成后如何验证

在终端运行：

```powershell
npm test
```

如果你希望进一步验证 API，可启动服务：

```powershell
npm start
```

另开一个终端执行：

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/tickets?priority=high"
```

## 8.5 期待结果

返回结果中应该只包含高优先级工单。

---

## 9. Step 4：Agent 实验任务 B - 为 POST /tickets 增加输入校验

## 9.1 校验要求

创建工单时，需要满足：

- `title`：不能为空
- `customer`：不能为空
- `priority`：只能是 `low`、`medium`、`high`

非法输入时，应返回：

- HTTP `400`
- 明确错误信息

## 9.2 推荐 Prompt

继续使用 **Agent** 模式，输入：

```text
Add validation for POST /tickets.

Requirements:
- title must be a non-empty string
- customer must be a non-empty string
- priority must be one of low, medium, or high
- return a clear validation error
- add or update tests
- run the tests when finished
```

## 9.3 完成后如何验证

先运行：

```powershell
npm test
```

然后启动服务：

```powershell
npm start
```

另开终端发送非法请求：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:3000/tickets" `
  -ContentType "application/json" `
  -Body '{"title":"","customer":"Contoso","priority":"urgent"}'
```

## 9.4 期待结果

你应看到一个 400 错误，并包含清晰的错误描述。

你也可以发送合法请求验证成功路径：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:3000/tickets" `
  -ContentType "application/json" `
  -Body '{"title":"Checkout page fails on Safari","customer":"Contoso","priority":"high"}'
```

---

## 10. Step 5：复盘 Ask / Plan / Agent 的使用场景

完成两个任务后，请回答以下问题：

### 10.1 Ask 适合什么

- 快速解释代码
- 找入口文件
- 看懂错误
- 识别 TODO 和改动点

### 10.2 Plan 适合什么

- 先梳理步骤再执行
- 控制 scope
- 让团队先审视方案

### 10.3 Agent 适合什么

- 需求边界清晰
- 需要跨文件修改
- 需要补测试
- 需要跑命令并验证结果

---

## 11. Step 6：可选扩展任务

如果你提前完成，可以尝试以下扩展任务：

### 扩展任务 1

新增一个 `GET /tickets/summary` 接口，按：

- status
- priority

输出统计信息。

### 扩展任务 2

为 `createTicket` 增加默认 SLA 字段，并补充测试。

### 扩展任务 3

请 Copilot 总结本次变更并生成一段 PR 描述。

推荐 Prompt：

```text
Summarize the changes in this project and draft a pull request description.
Include the problem, the solution, and how it was verified.
```

---

## 12. 常见问题与排查

## 12.1 Agent 没有按预期修改

处理方式：

1. 缩小任务范围
2. 用更明确的验收标准重试
3. 先用 Ask 理解问题，再用 Plan 约束步骤

## 12.2 Agent 修改太多

处理方式：

1. 明确说明“only change the minimum files needed”
2. 指定目标文件
3. 先用 Plan 审查步骤

## 12.3 不知道该不该批准工具调用

建议：

- 先阅读工具说明
- 对于读文件、跑测试通常可以批准
- 对于安装依赖或批量修改文件，需要先理解影响范围

---

## 13. 实验完成标准

完成实验后，你应满足以下标准：

- 能解释 Ask / Plan / Agent 的区别
- 能让 Agent 完成一个明确的小需求
- 能查看并理解 agent 的改动
- 能运行测试验证结果
- 能判断什么时候该给 agent 更高自治，什么时候要保留审批

---

## 14. 讲师收尾建议

讲师可用如下问题做收尾：

1. 你最愿意先在哪类任务中使用 Agent？
2. 你们团队更适合从 Default Approvals 还是 Bypass Approvals 开始？
3. 哪些任务你仍然更愿意先用 Ask / Plan，而不是直接 Agent？
