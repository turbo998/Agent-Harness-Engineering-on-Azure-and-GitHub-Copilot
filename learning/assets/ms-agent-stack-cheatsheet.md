<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 微软 Agent 技术栈速查（合作伙伴可转发版）

> 截至 **2026-06-22** 核实。版本/发布日期已自验（GitHub releases.atom）；star 数为采集时近似值。
> ⚠️ 可用性（尤其 Azure China vs Global）随租户/区域变化，落地前请按租户核实，本表不构成 GA 承诺。

## 一句话定位

> **新建生产 agent 项目 → 用 Microsoft Agent Framework (MAF)**，微软定位它为**整合 Semantic Kernel + AutoGen 谱系的开源后继**，并提供从两者的官方迁移指南。
> **Semantic Kernel 仍独立维护发版**（2026-06 仍在出 1.43.x，存量继续用、新工作迁 MAF）；**AutoGen 已冻结**（工作并入 MAF，勿新建）。
> 低代码/业务用户 → **Copilot Studio**；进 Teams/M365 → **M365 Agent SDK**；要托管运行时 → **Azure AI Foundry Agent Service**。
> agent 接**工具/数据走 MCP**，接**别的 agent 走 A2A**，两者正交、通常都要。

## 选型决策（一眼定位）

| 你的场景 | 推荐 | 备注 |
|---|---|---|
| 代码优先、生产级、多 agent 编排 | **MAF**（Python/.NET） | 默认答案 |
| 不想运维基础设施 | **Foundry-Hosted Agents** / Foundry Agent Service | MAF 加 2 行即托管 |
| 自托管、要完全控制 | MAF + Azure Functions / Durable Task / AKS | 看 ops 成熟度 |
| 业务用户、低代码、Power Platform | **Copilot Studio** | + CopilotStudioSamples（HITL/知识源）|
| 目标是 Teams / M365 / Copilot 界面 | **M365 Agent SDK**（microsoft/Agents）| 多通道 |
| 已建在 Semantic Kernel 上 | 继续跑 + 按迁移指南转 MAF | SK 没死 |
| 已建在 AutoGen 上 | 走 AutoGen→MAF 迁移 | 别再新建 AutoGen |

## 状态总表（发布日期自验 2026-06-22）

| 组件 | Repo | 状态 | 最新版本（截至） |
|---|---|---|---|
| **Microsoft Agent Framework** | microsoft/agent-framework | 🔥 主推、高频发版 | Python 1.9.0 / .NET 1.10.0 |
| Semantic Kernel | microsoft/semantic-kernel | ✅ 维护中、并入 MAF | py 1.43.1 (06-17) |
| AutoGen | microsoft/autogen | 🧊 **冻结** | v0.7.5 (2025-09-30) |
| M365 Agent SDK | microsoft/Agents | ✅ 活跃 | push 06-20 |
| Azure MCP servers | microsoft/mcp | ✅ 活跃 | Azure.Mcp.Server 3.0 beta (06-18) |
| Copilot Studio 样例 | microsoft/CopilotStudioSamples | ✅ 活跃 | push 06-10 |
| AI-Gateway（APIM+Foundry 治理 labs）| Azure-Samples/AI-Gateway | ✅ 活跃 | push 06-19 |

## MCP vs A2A —— 别搞混（讲清楚显资深）

| | **MCP**（Model Context Protocol） | **A2A**（Agent2Agent） |
|---|---|---|
| 连接 | agent ↔ **工具 / 数据 / 资源** | agent ↔ **别的 agent**（跨厂商）|
| 回答的问题 | "我的 agent 怎么安全读 Azure / 数据库 / API？" | "不同厂商的 agent 怎么协作？" |
| 微软姿态 | 一方 Azure / Fabric MCP server | MAF 支持 A2A 托管 |
| 治理 | modelcontextprotocol org | a2aproject/A2A（Linux Foundation）|
| 画图位置 | **纵向边**（agent↓工具/数据）| **横向边**（agent↔agent）|

## 编排词汇（统一术语，MAF 与 OpenAI SDK 已趋同）

`Sequential 顺序` · `Concurrent 并发` · `Handoff 交接` · `Group 群组协作` · `Guardrails 护栏` · `Human-in-the-loop 人在环` · `Sessions 会话态` · `Tracing/Observability 可观测(OpenTelemetry)` · `Checkpointing/Restartability/Time-travel 检查点/可重启/时间旅行` · `Middleware 中间件`

## POC 起步（MAF）

**Python**
```bash
pip install agent-framework
az login   # 用 AzureCliCredential / DefaultAzureCredential — 代码里不放 API key
```
```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
agent = Agent(client=FoundryChatClient(credential=AzureCliCredential()),
              name="HaikuAgent", instructions="You are an upbeat assistant.")
```

**.NET**
```bash
dotnet add package Microsoft.Agents.AI
dotnet add package Microsoft.Agents.AI.Foundry
dotnet add package Azure.AI.Projects
dotnet add package Azure.Identity
```

## 常见坑

- ❌ 别给新项目推 AutoGen（已冻结）。 ❌ 别说"SK 死了"（仍维护，会烧合作伙伴信任）。
- ⚠️ MCP≠A2A：一个接工具/数据（纵），一个接 agent（横）。
- ⚠️ Foundry 托管 vs 自托管是真分叉：托管省事少控制，自托管全控制重运维 —— 先问 ops 成熟度。
- ⚠️ 中国区：Foundry / Agent Service / 具体模型在 Azure China(21Vianet) 与 Global 可用性不同，**按租户/区域核实**，别承诺 GA。
- ⚠️ 引版本用**发布日期**别用 star 数（更能反映活跃度，且 API 限流）；查活跃度用 `releases.atom` 不用 REST API。

---
*来源：各 repo README/releases.atom，2026-06-22 自验可达。外部内容按资料处理。*
