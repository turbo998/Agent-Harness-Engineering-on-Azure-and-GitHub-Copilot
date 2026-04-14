# GHCP Workshop 120min — Agent 版（升级版）

Customer-facing GitHub Copilot workshop package for a 120-minute technical session.

## Workshop 主题

**GitHub Copilot：从 IDE 助手到 Agent 工作流 — AI-DLC · Harness Engineering · Multi-Agent 协作**

## Contents

| Path | Description |
| --- | --- |
| `GHCP_Workshop_120min_Agent版.pptx` | Main workshop deck (original) |
| `GHCP_Workshop_120min_升级版议程.md` | **升级版 120 分钟议程** |
| `GHCP_Workshop_120min_讲师Demo脚本.md` | Instructor demo script |
| `GHCP_Workshop_120min_实验操作手册.md` | Original lab manual (Ask/Plan/Agent basics) |
| `labs/lab1-aidlc-full-lifecycle.md` | **实验 1：AI-DLC 全生命周期闭环** |
| `labs/lab2-harness-engineering.md` | **实验 2：Harness Engineering 实操** |
| `labs/lab3-multi-agent-collaboration.md` | **实验 3：Multi-Agent 协作** |
| `lab-starter/` | Starter Node.js project with harness templates |
| `generate_ghcp_workshop_120min_agents_ppt.js` | Script used to generate the PPTX deck |

## 三个新增实验

### 实验 1：AI-DLC 全生命周期闭环（20 min）
用 GHCP 走完完整开发生命周期：
```
需求理解(Ask) → 规划(Plan) → 实现(Agent) → 测试(Agent) → Review(Ask) → PR描述(Ask)
```

### 实验 2：Harness Engineering（升级为 20–25 min 深水版）
通过结构化配置 + 工程反馈闭环驯服 Agent 行为：
- `copilot-instructions.md` — 全局项目规范
- Custom Agent — 专用角色（planner / test-engineer）
- Prompt File — 可复用任务模板
- Backpressure — tests / lint / CI 形成自我纠偏机制
- 结合热门参考：`github/awesome-copilot`、`walkinglabs/awesome-harness-engineering`、Copilot Customization Handbook

### 实验 3：Multi-Agent 协作（20 min）
多角色 Agent 串行协作：
```
Developer Agent → Test Engineer → Security Reviewer → Doc Writer
```

## Lab Starter 结构

```
lab-starter/
├── .github/
│   ├── copilot-instructions.md    # 全局 Agent 行为约束
│   ├── agents/
│   │   ├── test-engineer.md       # 测试专家 Agent
│   │   ├── security-reviewer.md   # 安全审查 Agent
│   │   └── doc-writer.md          # 文档生成 Agent
│   └── prompts/
│       └── add-endpoint.prompt.md # 可复用的"新增端点"模板
├── docs/
│   └── api.md                     # 文档占位（实验 3 生成）
├── src/
│   ├── app.js
│   ├── server.js
│   └── ticketStore.js
├── tests/
│   └── ticketStore.test.js
├── package.json
└── README.md
```

## Run the lab starter

```powershell
Set-Location .\lab-starter
npm install
npm test
npm start
```

## 升级版 vs 原版

| 维度 | 原版 | 升级版 |
|------|------|--------|
| 实操时间 | 30 min | 55 min |
| 实验数量 | 1 个（基础 Ask/Plan/Agent） | 3 个（AIDLC + Harness + Multi-Agent） |
| Harness Engineering | 未涉及 | copilot-instructions + custom agent + prompt file |
| Multi-Agent | 未涉及 | 4 角色串行协作 + Mission Control 介绍 |
| AI-DLC | 部分覆盖 | 完整 6 阶段闭环 |
| 讲解重心 | IDE 使用 + Agent 基础 | Agent 工作流 + 工程化治理 + 协作模式 |
