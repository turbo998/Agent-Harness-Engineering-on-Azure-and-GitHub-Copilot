# 托管 Harness 平台对比 —— AWS Bedrock AgentCore vs. Azure AI Foundry

> 触发来源：AWS《Harness 工程火遍硅谷，AgentCore 今天交卷!》（微信公众号，2026 年 4 月）—— 发布 **Bedrock AgentCore Managed Harness**。
> AWS 博客：https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/
> AWS 文档：https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html
>
> 研究日期：**2026 年 6 月**。所有 Azure 结论均引自 `learn.microsoft.com`；无法用一手来源核实的结论标注 **`[未核实]`**，**禁止以此向客户承诺**。

## 0. 这篇文档为什么存在

本 Workshop 把 harness 工程当作一门**自己动手搭**的功夫：你写 `chatmode.md`、`*.prompt.md`、`workflow.yml`，自己接工具、记忆、重试、护栏。这是一套**静态 harness**（见 [dynamic-harness-frontier.md](./dynamic-harness-frontier.md)）。

2026 年，云厂商开始把 harness **做成托管产品**。AWS 叫 **AgentCore Managed Harness**；微软的对位产品是 **Azure AI Foundry Agent Service**。两家的话术一模一样：*"你告诉 Agent 做什么，平台托管其余一切 —— 编排、工具、记忆、隔离、身份、可观测性。"*

对一个微软合作伙伴 SA，有两个问题最重要：

1. **逐项对比，Azure Foundry 能不能接住 AWS 这套话术？**（§2）
2. **我的客户到底用不用得上？** —— 即 **Azure 中国（世纪互联 21Vianet）** 这道闸门。（§3）

本文回答这两个问题，再把 **GitHub Copilot + 本 Workshop 的静态 harness 路线**放到同一张地图上（§4）。

## 1. AWS 的话术，一段话说完

AgentCore Managed Harness 主打十项能力：(1) 配置即编排，改配置不重新部署，"两个 API，Agent 就跑起来"；(2) 模型自由 —— Bedrock / OpenAI / Gemini / 任意 OpenAI 兼容模型，session 内随时切换且不丢上下文；(3) 工具即插即用 —— MCP Server、把 REST API 一键变工具的 Gateway、Browser、Code Interpreter、内联函数；(4) Skills 按需加载（markdown + 脚本知识包）；(5) 自带 Docker 镜像；(6) Shell 命令**零 token 成本**；(7) 断点续跑 + 持久化文件系统 + 跨会话记忆；(8) 每 session 独立 **Firecracker microVM** 隔离 + Identity + Observability；(9) 不锁定 —— 基于开源 **Strands Agents** 框架，随时导出自部署；(10) **无 Harness 附加费**，只按底层用量计费。

这套话术确实强。下面诚实的结论是：**Azure 对其中几乎每一条都有真实答案** —— 但成熟度散落在 GA 与 Preview 之间，而中国区的故事会改写一切。

## 2. 能力对照 —— AWS 十项能力 → Azure Foundry

> 术语：原 *Azure AI Agent Service* 现已更名 **Foundry Agent Service**。它把 Agent 分成 **Prompt agents**（声明式、平台编排、GA）与 **Hosted agents**（你的代码/容器跑在托管沙箱里、Preview）。

| # | AWS AgentCore | Azure AI Foundry 对位 | 工作方式 | 状态（2026-06） | 中国区(21Vianet) |
|---|---|---|---|---|---|
| 1 | 托管编排（配置即用，不重新部署） | **Prompt agents** | 模型+指令+工具皆为配置；平台托管编排，改配置不重新部署。 | **GA** | ❌ 不可用 |
| 2 | 模型自由，不锁定 | **Foundry 模型目录** + **Model router** | 目录覆盖 OpenAI、Llama、Mistral 等；router 按调用选模型；每 Agent 的模型可配置切换。*AWS 式 session 内带上下文热切换* = **`[未核实]`**。 | 目录 **GA**；router `[未核实]` | ❌ |
| 3 | 工具即插即用 | **Foundry 工具套件** | **OpenAPI 工具**（REST→工具，≈ AWS "Gateway"）；**MCP 工具**；**Browser 自动化**（Playwright，以 MCP 暴露）；**Code Interpreter**（沙箱 Python）；**函数调用** + **Azure Functions**。 | Code Interpreter / OpenAPI / Functions **GA**；MCP / Browser **Preview** | ❌ |
| 4 | Skills 按需加载 | **Foundry Skills** | 采用**开放 Agent Skills 规范（`SKILL.md` + YAML）**—— 与本 Workshop 已在教的格式一致。三种加载模式是否全对齐 = `[未核实]`。 | **Preview** | ❌ |
| 5 | 自带 Docker 镜像 | **Hosted agents** | 自带代码/容器，跑在托管的、每 session 隔离的沙箱里，文件系统持久化。最接近 AWS 自带镜像。 | **Preview** | ❌ |
| 6 | Shell 命令零 token 成本 | **Hosted agents** 沙箱 | 持久化文件系统（`$HOME`、`/files`），确定性操作直接跑。明确的"零 token shell"营销说法 = `[未核实]`；但架构上支持。 | **Preview** | ❌ |
| 7 | 断点续跑 + 持久记忆 | **Hosted agents**（缩容到零、有状态恢复）+ **Memory** | Hosted agents 自动暂停/恢复，文件系统持久化；**Memory Store API** 做抽取→整合→检索，跨会话短期+长期记忆。 | 均 **Preview** | ❌ |
| 8 | 每 session 隔离 + 身份 + 可观测 | **Standard agent setup（自带 VNet）** + **Entra ID** + **Azure Monitor / App Insights 链路追踪** | 每 session 的 VM 级隔离沙箱（*"Firecracker 等效 microVM"* 这个命名 = `[未核实]`）；Entra ID / 托管标识；网络注入；OpenTelemetry 追踪。 | 隔离/身份/追踪 **GA** | ❌ |
| 9 | 不锁定（开源框架，导出自部署） | **Microsoft Agent Framework**（开源） | 开源框架，**Semantic Kernel + AutoGen 的继任者**。Azure 真正的可移植性故事，对位 AWS Strands。 | 框架 **GA / 开源** | 框架可任意部署；**托管服务 ❌** |
| 10 | 无 Harness 附加费 | **按量计费** | Prompt agents：推理+工具用量；Hosted agents 另加容器算力；Code Interpreter 按 session 额外计费。未确认有单独"harness 附加费"——*但专门定价页 404*，逐项定价 = `[未核实]`。 | n/a | ❌ |

**这张表怎么读：** 在 **Azure Global** 上，能力对位确实接近。声明式路线（Prompt agents、工具、身份、追踪）**今天就是 GA**；端到端复刻 AWS 那套完整"托管 harness"体验的部分（Hosted agents、Skills、Memory、MCP、Browser）大多还在 **Preview**。Azure 拥抱开放 Skills + MCP，意味着本 Workshop 产出的物料（`SKILL.md`、MCP 工具）对 Foundry **向前兼容** —— 这是实打实的资产，不是巧合。

## 3. ⚠️ 中国区闸门 —— 向客户报价前必读

**截至 2026 年 6 月，Azure AI Foundry Agent Service 在 Azure 中国（世纪互联 21Vianet）不可用。**

- Azure 中国服务可用性页面，在 "AI + 机器学习" 下**只列出** Azure 机器学习、Azure AI 语音、Translator。**Foundry Agent Service、Foundry Models、Agent 工具均缺席。**
- Foundry 区域支持页面把 **US Government** 列为唯一主权云；**没有 21Vianet / 中国区**。`[未核实]` —— 旁证信号；引用前请对照实时的 Foundry 区域支持页面重新确认。

**对面向中国市场的伙伴意味着什么：** 能力 #1–#8 和 #10（托管服务 + 工具 + 记忆）**今天无法在 Azure 中国交付。** 唯一可移植的路径是 **#9 —— 开源的 Microsoft Agent Framework，自部署在 Azure 中国算力 + 一个 Azure OpenAI 等效端点上** —— 这只给你**编程模型**，**拿不到**托管 harness 的红利（你又回到了自己搭运行时、隔离、可观测性的状态）。

> SA 规则：任何"Foundry agents 跑在 Azure 中国"的说法，在微软正式公布 21Vianet 可用性之前，一律按 **`[未核实]` / 大概率为假**对待。**绝不能让客户拿它去排路线图。** 这正是必须**大声失败**的那类未核实可用性结论。

## 4. GitHub Copilot + 本 Workshop 站在哪里

托管 harness 平台（AWS AgentCore、Azure Foundry）和本 Workshop 教的 **GitHub Copilot 静态 harness** 路线，**不是竞品 —— 是不同的层**：

| 维度 | 托管 Harness（AgentCore / Foundry） | GitHub Copilot 静态 harness（本 Workshop） |
|---|---|---|
| 谁写编排 | 平台，根据你的配置 | **你**，写在 `chatmode.md` / `*.prompt.md` / `workflow.yml` |
| 在哪运行 | 厂商托管沙箱 / microVM | 你的 repo、你的 CI（GitHub Actions）、你的 VM / Container Apps |
| 主要面向 | 生产级 Agent **服务**（你的 App 调的 API） | **开发者内循环** —— 在 IDE + PR 里写码、评审、发布 |
| 工具模型 | MCP + OpenAPI + Code Interpreter，厂商托管 | MCP + 你自己的工具，**托管标识握在你手里** |
| Skills | `SKILL.md` 包（同一开放规范） | `SKILL.md` 包（同一开放规范）—— **双向可移植** |
| 中国区可用 | **Foundry ❌（21Vianet）**（截至 2026-06） | 自托管 runner 任意区域可跑；**GitHub Copilot 是全球 SaaS** —— 面向中国客户请核实企业数据驻留/合规 `[未核实]` |
| 最适合 | "我要一个托管 Agent 端点给我的 SaaS" | "我要让工程团队更快交付，且在 PR 里可审计" |

**Lab 2/3 的教学要点：** harness 工程作为一门**技能**，在这三者之间是通用的。你在这里搭出来的物料 —— 角色定义、prompt 文件、**Quarantine** 读/执分离、MCP 工具、`SKILL.md` 包 —— 正是日后交给 Foundry Hosted agents 或 AgentCore 的东西。你学的不是某个 Copilot 专属技巧，而是**厂商中立的 harness 语汇**，然后再决定在哪里运行它。

**对中国伙伴尤其务实的结论：** 托管 harness 平台目前基本是 **Global 云的故事**，所以**在 GitHub Copilot + 自托管 runner 上自建静态 harness**，不只是教学装置 —— 在 21Vianet 边界内，它今天就是**更能落地**的选项。

## 5. 诚实的缺口（请带着往下走）

以下内容在研究中**未能**用一手来源核实，特此标注，避免有人当事实转发：

- Azure **session 内带上下文热切模型**（#2）—— 未确认；Azure 已核实的强项是按调用路由，而非 AWS 式实时切换。
- **"零 token shell"** 的明确说法（#6），以及 **microVM / Firecracker 等效**的虚拟化命名（#8）。
- **三种 Skills 加载模式**（#4）逐一确认。
- **Foundry agent 逐项定价**（#10）—— 专门定价页返回 404，只确认了计费*模型*。

任何面向客户的复用之前，请对照 Azure 实时页面重新核实定价行与 model-router 结论，并复查 21Vianet 可用性（万一微软在 2026 年 6 月之后已上线）。

---

### 来源

- AWS AgentCore harness 文档 —— https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html
- AWS 发布博客 —— https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/
- Foundry Agent Service 运行时组件 —— https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components
- Foundry Hosted agents —— https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents
- Foundry 工具（MCP）—— https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/model-context-protocol
- Foundry Memory —— https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-memory
- Microsoft Agent Framework —— https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview
- Azure 中国服务可用性 —— https://learn.microsoft.com/en-us/azure/china/concepts-service-availability
