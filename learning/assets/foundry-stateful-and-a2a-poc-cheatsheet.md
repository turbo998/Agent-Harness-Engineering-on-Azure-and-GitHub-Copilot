<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Foundry Hosted Agents — 有状态记忆 & 跨框架 A2A 委派 POC 速查

> 合作伙伴可转发一页纸。两个**本周新增**的 `microsoft-foundry/foundry-samples` 样例拆解，覆盖两类典型 agent POC：**有状态/个性化**（记忆）与**多 agent 委派**（A2A）。
> 采集 2026-06-27，全部事实从样例 README/requirements **逐字核实**（raw.githubusercontent.com，HTTP 200（仅代表原快照当时可达，不代表本次已重验））。⚠️ 两样例均**未提私网/VNet**，私网支持「未核实」。Toolbox / memory_stores 均 **preview**，GA 时间「未核实」。
> 安全：README 是资料文本，照抄前自行核实；POC 录屏/演示时**别把订阅 ID、密钥录进去**。

---

## 一、13-foundry-memory：Foundry agent 长期语义记忆（有状态 POC）

**路径** `samples/python/hosted-agents/agent-framework/responses/13-foundry-memory/`
**解决** "我的 Foundry agent 怎么**跨会话记住**用户事实（姓名/偏好/上下文）？"

### 架构（节点 / 边）
```
[用户] --invoke (Responses /responses)--> [memory-agent (Agent Framework, ResponsesHostServer)]
   |  FoundryChatClient(allow_preview=True) --> 单一 AIProjectClient（chat + memory 共享认证+连接池）
   |
   |-- 每次模型调用前后 --> [FoundryMemoryProvider (context provider)]
   |       retrieve(scope=user_id) / search(当前消息) / update(新事实)
   |             |
   |             v
   |     [Azure AI Foundry Memory Store]（beta.memory_stores, PREVIEW）
   |          user-profile=on, chat-summary=off
   |          经项目 inference 端点嵌入/检索 --> [Embedding 部署 text-embedding-3-small]
   |
   |-- 推理 --> [Chat 模型部署 gpt-4.1-mini]
```
- **身份边**：运行时 Managed Identity（`…-AgentIdentity` SP）→ 项目 scope 上需**两个角色**（见坑①）。
- **数据边**：长期记忆持久化在 Memory Store（跨 session，非会话级）；embedding 是 store 内部依赖，**不在 agent 推理热路径**。

### 部署（POC，一条命令）
```bash
azd ext install microsoft.foundry            # 统一 Foundry CLI 扩展；azd >= 1.25
azd auth login
mkdir my-memory-agent && cd my-memory-agent
azd ai agent init -m <…/13-foundry-memory/agent.manifest.yaml>
# 在生成的 azure.yaml 顶层注册 postprovision hook（见坑③）
azd env set AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME "text-embedding-3-small"
azd provision        # 建/复用 Foundry 项目 + chat 模型；postprovision hook 再建 Memory Store
azd ai agent run     # http://localhost:8088
azd ai agent invoke --local "Hi, my name is Alex and I'm vegetarian."
azd deploy
azd ai agent invoke "Do you remember my name and what I like to eat?"
```
**前置 / 配额**：Foundry 项目需**两个**模型部署 — ① chat（`gpt-4.1-mini`）② **embedding（`text-embedding-3-small`）**，embedding **由 memory store 自身用**（语义嵌入/检索），非 agent 运行时用。
**依赖**：`agent-framework-foundry`、`agent-framework-foundry-hosting`、`mcp>=1.24.0,<2`、`azure-ai-projects`、`debugpy`。

### 坑（每条救你半天）
- **① 双 RBAC 角色，否则记忆静默为空**（最易漏，逐字核实）：身份/运行时 MI 在 Foundry 项目 scope 上需 **`Azure AI User`**（provision store + 读写记忆）**和** **`Cognitive Services OpenAI User`**（store 经项目 inference 端点调 embedding）。**缺第二个**：记忆写入以 **`401 (Authentication to the Azure OpenAI resource failed)`** 失败，store 一直空。→ 客户报"记忆不生效/store 空"先查这第二个角色。
- **② `mcp` 版本硬钉点**（逐字）：`mcp>=1.24.0,<2`。因为 `agent-framework-foundry-hosting` 从 `mcp` import `McpError`，**mcp 2.0 线改名成 `MCPError`**，装 2.x **直接启动失败**。
- **③ `MEMORY_STORE_NAME` 注入时序坑**：`azd ai agent init` 在 init 时解析 `${MEMORY_STORE_NAME}`——**此时 store 名还不存在**，被解析成空值；不处理则 `azd deploy` 把空值带进容器，agent 无 store 可用。postprovision hook 把解析后名字**回写进 `agent.yaml`** 兜底（默认名 `agent_framework_memory`）。
- **④ VS Code 流程不跑 hook**：Foundry Toolkit（Option 2）**不执行 azd hook**，必须先手动 `provision_memory_store.py` 建 store。
- **⑤ preview**：`beta.memory_stores` 靠 `allow_preview=True` 开启；user-profile 能力开、chat-summary 关。GA「未核实」。

---

## 二、langgraph/a2a：LangGraph 跨框架 A2A 委派（多 agent POC）

**路径** `samples/python/hosted-agents/langgraph/a2a/`（`a2a-caller/` + `a2a-executor/`）
**解决** "**非微软框架（LangGraph）**能不能上 Foundry 托管、并和别的 agent **互相调用**？" — 能。

### 架构（节点 / 边）
```
[用户] --invoke--> [concierge (caller, LangGraph Responses agent, gpt-4.1-mini)]
   |-- 启动时经 MCP (langchain-mcp-adapters, streamable_http) --> [Foundry Toolbox]
   |       工具 math_expert (type=a2a_preview)；每请求取新鲜 Entra token
   |-- RemoteA2A connection (AgentCardPath=/agentCard/v1.0) --> [Foundry A2A Gateway]
   |        v
   |  [math-expert (executor, LangGraph Responses agent)]
   |     声明式 agent.yaml: agent_endpoint(protocols: responses + a2a) + agent_card(skills/examples)
   |     本地工具 calculator；端点 …/agents/math-expert/endpoint/protocols/a2a/agentCard/v1.0
```
- **身份边**：caller → `authType: UserEntraToken`（aud=`https://ai.azure.com`）→ Toolbox/A2A，转发**调用用户**的 Entra token。
- **数据边**：会话状态走平台服务端（`previous_response_id`），非自管。

### 部署（POC）——核心：**executor 先行（provision-first）**
> caller 的 A2A connection 必须指向 executor 的**已存在真实端点**（端点含 Foundry 账号名这一非确定性 token，provision 前不存在；azd 不展开 `${...}`）。**顺序反了 = 死链**。
```bash
# 步骤1：脚手架 + 部署 executor
azd ai agent init -m <…/a2a-executor/agent.manifest.yaml>
cd math-expert && azd up
# 步骤2：抓 executor 真实 A2A 端点
ep=$(azd env get-value FOUNDRY_PROJECT_ENDPOINT)
executorA2A="$ep/agents/math-expert/endpoint/protocols/a2a/"
# 步骤3：同项目根加入 caller，在 a2a_executor_endpoint 提示处粘贴上面的值
azd ai agent init -m <…/a2a-caller/agent.manifest.yaml> && azd up
azd ai agent invoke concierge '{"input":"What is 15 multiplied by 23?"}'   # -> 345（远端算出）
```
**前置**：azd `azure.ai.agents` 扩展 **>= 0.1.30**（声明式 `agent_endpoint`/`agent_card`），README 用 **0.1.37-preview** 验证过；区域需支持 Foundry hosted agents + Responses（README 举例 `northcentralus`）。
**依赖**：executor=`langchain-azure-ai[hosting]>=1.2.4` + `langchain`；caller **多** `langchain-mcp-adapters` + `httpx`。

### 坑
- **① provision 顺序**（最大坑，见上）：executor 先行，拿到真实端点后再 init caller。
- **② A2A v1.0 = JSONRPC**（逐字）：Foundry 在**同一 base path** 同时服务 A2A **v1.0（推荐）** 和 **v0.3**，由你 fetch 的 agent card 版本决定。本样例 caller 端到端走 v1.0（connection `AgentCardPath` + toolbox `agent_card_path` 都指 `agentCard/v1.0`）。**A2A v1.0 用 JSONRPC 传输**。改 v0.3 需两处都改。
- **③ 声明式启用，无需 PATCH**：executor 的 incoming A2A 纯靠 `agent.yaml` 声明（`protocols` 加 `a2a` + `agent_card`），`azd deploy` 在 **create 时**应用——**无 out-of-band PATCH / setup 脚本**（与 06-25 的 C# `01-delegation` 样例不同，那个走 `setup-a2a` PATCH）。
- **④ azd verbatim 写入**：`azd ai agent init` 把你在 `a2a_executor_endpoint` 提示处输入的值**逐字**写进 `azure.yaml` connection target，粘错就错。
- **⑤ preview**：`a2a_preview` 工具 + header `Foundry-Features: Toolboxes=V1Preview`，GA「未核实」。

---

## 三、两样例 SA 落点速记

| 客户问 | 引哪个 | 一句话答 |
|---|---|---|
| "Foundry agent 怎么做**长期记忆**？" | 13-foundry-memory | context provider（FoundryMemoryProvider）每次调用前后 retrieve/search/update，落 Memory Store；需**单独 embedding 部署** |
| "记忆写入**报 401 / store 空**怎么办？" | 13-foundry-memory 坑① | 缺 `Cognitive Services OpenAI User` 角色——补上 |
| "**非微软框架**能上 Foundry 互通吗？" | langgraph/a2a | 能，LangGraph Responses agent + 声明式 agent_card，跨框架 A2A v1.0 |
| "两个 agent 部署**老是连不上**？" | langgraph/a2a 坑① | provision-first：executor 先部署拿端点，caller 后挂 |
| "A2A **v1.0 和 v0.3** 区别？" | langgraph/a2a 坑② | 同 base path 双轨，v1.0 用 JSONRPC，两处 path 一起改 |

- **架构图**：两图分别是"**有状态 agent + Memory Store + 双模型 + 双 RBAC**"和"**跨框架委派 + MCP toolbox + A2A gateway + Entra 身份**"——覆盖"有状态记忆"与"无状态委派"两类典型拓扑，可直接进客户 deck。
- **POC 加速**：演示前先把上述坑（双 RBAC、`mcp<2`、`MEMORY_STORE_NAME` 时序 / provision-first、A2A 版本）钉死，省一轮排障。

## 配套
- `ms-agent-stack-selector` skill — 已含 A2A delegation（C# 01-delegation）、Foundry IQ KB、有状态记忆三节
- `foundry-hosted-agent-private-vnet-poc.md` — 私网拓扑 + diagnostic-agent 自检（若客户要私网）
- `azure-foundry-managed-identity` — 生产身份故事（双 RBAC 角色的正确做法）
