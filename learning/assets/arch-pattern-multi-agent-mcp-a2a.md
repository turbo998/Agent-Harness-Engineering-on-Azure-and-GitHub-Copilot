<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 架构图模式：企业级多 Agent 参考拓扑（MCP 纵 / A2A 横）

> 可复用的"agent 系统"架构图骨架。截至 2026-06-22。
> 核心心法：**MCP 是纵向边（agent→工具/数据），A2A 是横向边（agent↔agent）**。
> 画任何 agent 架构图先摆这两条轴，缺一条就主动问客户是不是漏了。

## 何时用
- 客户问"多 agent 系统怎么搭""agent 怎么接我们的数据""不同 agent 怎么协作"
- POC/方案要配一张参考架构图
- 评审客户已有 agent 设计（用这张图当 checklist 找缺口）

## 五层骨架（从上到下）

```
┌─────────────────────────────────────────────────────────────┐
│  L1 体验层  Teams / M365 / Copilot / Web / 语音               │
│            └─ M365 Agent SDK · Copilot Studio · DevUI         │
├─────────────────────────────────────────────────────────────┤
│  L2 编排层  Microsoft Agent Framework (MAF)                   │
│     Orchestrator Agent                                        │
│       ├─Sequential ├─Concurrent ├─Handoff ├─Group            │
│       Guardrails · HITL · Sessions · Checkpoint · Middleware  │
│                                                               │
│     [Agent A] ◄──────── A2A（横向：跨 agent/跨厂商）────► [Agent B (外部/3P)]│
├─────────────────────────────────────────────────────────────┤
│  L3 模型层  Azure AI Foundry / Azure OpenAI                   │
│            (DefaultAzureCredential / Managed Identity 认证)   │
├──────────────┬──────────────────────────────────────────────┤
│  L4 工具/数据 │   每条都是 MCP 纵向边（agent↓工具/数据）       │
│   (via MCP)  │   Azure MCP Server · Fabric MCP · 自建 MCP    │
│              │   └→ Azure 资源 / DB / API / SharePoint / 文件 │
├──────────────┴──────────────────────────────────────────────┤
│  L5 治理/横切  APIM AI-Gateway · OpenTelemetry 可观测         │
│              · Entra ID 身份 · 私网/VNet · 配额/限流           │
└─────────────────────────────────────────────────────────────┘
```

## 组件库（画图时的"零件清单" + 微软对应物）

| 角色 | 微软落地组件 | 图标提示 |
|---|---|---|
| 体验/通道 | M365 Agent SDK, Copilot Studio | 设备/聊天气泡 |
| 编排引擎 | Microsoft Agent Framework | 中央菱形/枢纽 |
| 单个 agent | MAF Agent | 圆角方块 + 机器人 |
| agent↔agent | **A2A 协议**（横向箭头）| 双向横箭头，标 "A2A" |
| agent→工具/数据 | **MCP server**（纵向箭头）| 向下箭头，标 "MCP" |
| 模型 | Azure AI Foundry / Azure OpenAI | 芯片/脑 |
| 托管运行时 | Foundry-Hosted Agents / Agent Service | 云托管框 |
| 网关/治理 | Azure APIM (AI-Gateway) | 闸门 |
| 身份 | Entra ID + Managed Identity | 盾/钥匙 |
| 可观测 | OpenTelemetry | 仪表盘 |

## 三种常见变体（按客户场景选）

1. **单 agent + 工具型**（最简 POC）：L2 只有 1 个 agent，去掉 A2A 横向边，保留若干 MCP 纵向边。适合"我就想让 agent 查我们的数据库"。
2. **编排型多 agent（内部）**：L2 一个 Orchestrator + 多 worker agent，内部走 MAF handoff/group，**不一定需要 A2A**（A2A 主要用于跨厂商/跨边界）。
3. **跨厂商联邦**：本方 MAF agent 通过 **A2A** 接客户/第三方 agent，**这时 A2A 横向边是主角**，每方各自用 MCP 接自己的数据。

## 画图执行（配合现有 skill）
- 暗色 SVG → 调 `architecture-diagram` skill
- 手绘草图 → 调 `excalidraw` skill
- 渲染前先确认：① MCP 纵向边齐了吗 ② 该有 A2A 横向边吗 ③ 认证用 Managed Identity 标了吗 ④ 治理层（网关/可观测/身份）画了吗

## 评审 checklist（拿这张图审客户设计找缺口）
- [ ] 数据访问是不是裸连？应走 MCP server 而非 agent 直连密钥
- [ ] 认证是不是硬编码 key？应 Managed Identity / DefaultAzureCredential
- [ ] 多 agent 是不是该上 A2A 还是内部 handoff 就够（别过度设计）
- [ ] 有没有 HITL/Guardrails（高风险动作必须人在环）
- [ ] 可观测性（OpenTelemetry）有没有
- [ ] 长任务有没有 checkpoint/可重启
- [ ] 中国区：用到的 Foundry/模型在目标租户区域 GA 吗（标"未核实/需核实"）

---
*来源：MAF README、microsoft/mcp、a2aproject/A2A，2026-06-22 自验。外部内容按资料处理，不含任何密钥。*
