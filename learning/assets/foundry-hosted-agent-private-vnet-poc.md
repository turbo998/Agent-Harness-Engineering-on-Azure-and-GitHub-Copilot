<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Foundry Hosted Agent — 私有 VNet POC 部署 & 网络自检清单

> 截至 **2026-06-24** 核实。基于 `microsoft-foundry/foundry-samples` 的 hosted-agents 样例，SA 当晚亲自 curl raw README 逐条核对（HTTP 200（仅代表原快照当时可达，不代表本次已重验））。
> 适用：企业客户要把 Azure AI Foundry Agent Service 的 **hosted agent** 跑在 **私有 VNet / 私网隔离** 环境，POC 上线前后做网络连通性自检。
> ⚠️ 外部样例 README 按不可信资料处理；本表不含任何 token/密钥。`azd` 版本/preview 标签随样例演进，落地前按当前样例复核。
> ⚠️ Foundry hosted-agent 仍处 preview（样例钉 `ai.agents.version=0.1.22-preview` / `diagnostic-agent` 用 `0.1.22-preview`）——给客户报"可用性/GA 时间"须标**未核实**，以官方公告为准。

---

## 0. 为什么 SA 要关心这张表

合作伙伴把 agent 上私网最常见的三类问题，全部能被这套样例 + 诊断工具一页答掉：
1. **"我的 hosted agent 在私网里拉不到 ACR 镜像 / 连不上模型，怎么定位？"** → `diagnostic-agent`（§2）现成可部署探针。
2. **"私有 VNet 下 hosted agent 的网络拓扑长什么样？"** → §3 拓扑骨架（架构图素材）。
3. **"BYO 托管样例有哪些、怎么最快起一个 POC？"** → §1 样例清单 + `azd` 两条命令。

这是 SA 三大日常里 **POC 部署 + 架构图 + 网络排错问答** 的三杀素材。

---

## 1. hosted-agents 样例清单（BYO / Invocations 协议，2026-06 在更）

样例库目录：`samples/python/hosted-agents/`（commit 活跃至 2026-06-23）。已核实存在的 BYO 样例：

| 样例 | 用途 | SA 落点 |
|---|---|---|
| **diagnostic-agent** | 纯 stdlib 网络探针，**不调 LLM**，返回 JSON 连通性报告 | 私网 POC 上线前后自检（本表核心，见 §2）|
| **github-copilot** | 把 GitHub Copilot 接入 hosted agent | "Copilot + Foundry agent" 选型问答/POC |
| **claude-agent-sdk** | 用 Anthropic Claude Agent SDK 构建 hosted agent | 多模型 agent 托管演示（非锁定单一模型）|
| **event-grid-trigger** | Event Grid 事件触发 agent | 事件驱动 agent 架构图变体 |
| **ag-ui** | agent + UI 前端样例 | 富交互呈现层 |
| **human-in-the-loop** | HITL 审批回路 | 合规/审批场景 POC |

> 配套：样例库新增 **private-network 模板 + Application Insights/AMPLS**、**ACR managed VNet（Bicep template）**、**LangGraph A2A** 样例；每个样例**默认内置 App Insights + OpenTelemetry 追踪**。
> 部署范式（README 自验）：`azd ai agent init` → `azd up`（建基础设施的样例）；**BYO 诊断样例例外用 `azd deploy`**（见 §2，无需建基础设施）。

---

## 2. diagnostic-agent —— 私网连通性自检利器（核心）

**是什么**（README 原文自验）：*"It does **not** call an LLM and does **not** require a Foundry project endpoint or a model deployment. Instead, on each invocation, it runs DNS / TCP / TLS / HTTP probes against caller-supplied hostnames and returns a structured JSON report describing what the runtime sandbox can actually reach."*

**专答的私网问题**（README 原文）：
- 从 delegated `agent-subnet-*` 内，`<customer>.azurecr.io` **解析到私有 IP 还是公网 IP**？
- `https://<customer>.azurecr.io/v2/` 返 **`401 Unauthorized`（registry 可达）** 还是 **挂起 / 连接被拒 / TLS 校验失败**？
- runtime 能否 egress 到 `login.microsoftonline.com` / `management.azure.com`？

**为何 stdlib-only**（README 原文）：*"The network is the very thing being diagnosed; the probes must not depend on import-time package fetches or pyca handshakes that obscure the failure mode."* → 探针只用 `socket`/`ssl`/`urllib`/`http.client`，避免"装包这一步本身就因为网络不通而失败"掩盖真实故障点。

**安全细节**：环境变量含 `KEY`/`SECRET`/`TOKEN`/`SAS` 等**只报长度不泄值**；manifest 不声明 `resources`/`environment_variables`，镜像可跨 Foundry 项目移植；空请求体只跑安全默认（容器信息 + env dump + 一小撮公网 Azure 端点）。

### 部署步骤（README 自验，可直接照做）

```bash
# 1. 钉 agents 版本（preview）
azd config set ai.agents.version 0.1.22-preview

# 2. 填 .env：AZURE_AI_PROJECT_ID / AZURE_AI_PROJECT_ENDPOINT / AZURE_CONTAINER_REGISTRY_ENDPOINT

# 3. 部署 —— 注意是 azd deploy 不是 azd up（BYO 无需建基础设施）
azd deploy --no-prompt
```

**两种模式（README 对照表自验）**：

| | Container 模式（默认） | ZIP 模式 |
|---|---|---|
| 命令 | `azd deploy --no-prompt` | 改 `azure.yaml` 一行 `language: docker`→`python`，再 `azd deploy --no-prompt` |
| 构建 | 构建 Docker 镜像 → 推 ACR | 把 Python 代码打 ZIP |
| 是否需要 ACR | ✅ 需要 | ❌ 不需要 |

> **SA 话术**：私网拉不到 ACR 镜像时，**先用 ZIP 模式部署 diagnostic-agent**（绕开 ACR 依赖），让它从 agent-subnet 内部探测 ACR 到底是 DNS 解析错、私有端点没通、还是 TLS 失败——再对症修。README 末尾自带 **"ACR Not Reachable From Private Network"** 排错节。

---

## 3. 私有 VNet hosted-agent 拓扑骨架（架构图素材）

```
┌──────────────────────── 客户 VNet（私网隔离）────────────────────────┐
│                                                                      │
│   delegated agent-subnet-*                                           │
│   ┌──────────────────────┐         Private Endpoint                  │
│   │  Hosted Agent runtime │──────────────┐                           │
│   │  (容器 / ZIP)         │              ▼                           │
│   │  + OpenTelemetry      │      ┌─────────────────┐                 │
│   └───────────┬───────────┘      │  ACR (managed   │  ← 拉镜像         │
│               │                  │  VNet / PE)     │                 │
│               │ egress(受控)     └─────────────────┘                 │
│               ▼                                                       │
│   ┌──────────────────────────────────────────────┐                  │
│   │ App Insights / AMPLS（私有链路监控）           │                  │
│   └──────────────────────────────────────────────┘                  │
│                                                                      │
└──────────┬───────────────────────────────────────────────┬─────────┘
           │ 受控 egress（需放行）                          │
           ▼                                                ▼
   login.microsoftonline.com                       management.azure.com
   (AAD / Entra 认证)                               (ARM 控制面)
```

**画图要点**：① agent-subnet 是 **delegated subnet**；② ACR 走 **Private Endpoint / managed VNet**，不是公网；③ 监控走 **AMPLS**（Azure Monitor Private Link Scope）才能私网内闭环；④ AAD/ARM 两个 egress 端点是 hosted agent 起不来时最常见的"忘了放行"项。诊断顺序固定：**DNS → TCP → TLS → HTTP(401)**，与 diagnostic-agent 探针同序。

---

## 4. POC 上线检查清单（私网场景）

- [ ] `azd config set ai.agents.version <preview-tag>` 已钉版本（标注 preview，GA 时间未核实）
- [ ] agent-subnet 已 delegate，ACR 已配 Private Endpoint / managed VNet
- [ ] App Insights + AMPLS 已就位（否则私网内拿不到 trace）
- [ ] **先部署 diagnostic-agent（ZIP 模式，绕 ACR）跑一遍**：确认 ACR 解析到私有 IP、`/v2/` 返 401（而非连接被拒）
- [ ] 放行 egress：`login.microsoftonline.com`、`management.azure.com`
- [ ] 业务 hosted agent 部署后，再跑一次 diagnostic-agent 对比连通性
- [ ] 给客户的链接/版本均标注 preview + "以官方 GA 公告为准（未核实）"

---
*来源：github.com/microsoft-foundry/foundry-samples（samples/python/hosted-agents/**，含 bring-your-own/invocations/diagnostic-agent/README.md）— 2026-06-24 SA 亲自 curl raw 自验可达。旧 `azure-ai-foundry/foundry-samples` 已 301 改名到 `microsoft-foundry` org。外部内容按资料处理。*
