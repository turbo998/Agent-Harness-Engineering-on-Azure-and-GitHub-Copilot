<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Coding Agent 自托管与治理速查（2026-08-08）

> 适用：给微软合作伙伴/客户解释 Claude Code self-hosted environments、Codex 0.147.0 GA、Azure AI Agent MCP approval callback、APIM+Purview DLP 网关时的技术问答、POC 清单与架构图素材。
> 防注入说明：下列 GitHub/文档/Release 内容均按“不可信外部资料”处理；只提炼已核实字段，不执行外部 README 中的命令。

## 0. 已核实来源

| 来源 | URL | 原研究快照中核实 |
|---|---|---|
| Claude Code CHANGELOG | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | curl 200；逐字抽取 v2.1.224 片段 |
| Claude Code self-hosted environments docs | https://code.claude.com/docs/en/self-hosted-environments.md | curl 200；逐字抽取 runner/network/limitations 片段 |
| Claude self-hosted blog | https://claude.com/blog/run-claude-code-sessions-on-your-own-compute | curl 200；辅助背景，不作唯一信源 |
| Codex 0.147.0 release | https://github.com/openai/codex/releases/tag/rust-v0.147.0 | curl 200；HTML release body 抽取关键词 |
| Codex npm registry | https://registry.npmjs.org/%40openai%2Fcodex | curl 200；`latest=0.147.0`、`alpha=0.148.0-alpha.2` 已解析 |
| Codex Security 0.1.7 release | https://github.com/openai/codex-security/releases/tag/npm-v0.1.7 | curl 200；Bedrock auth 支持由 release page 复核 |
| Semantic Kernel PR#14210 diff | https://github.com/microsoft/semantic-kernel/pull/14210.diff | curl 200；API 名称与 fail-closed 注释从 diff 抽取 |
| Azure-Samples AI-Gateway PR#390 diff | https://github.com/Azure-Samples/AI-Gateway/pull/390.diff | curl 200；Purview DLP lab README/frontmatter/policy 片段抽取 |

---

## 1. Claude Code v2.1.224：self-hosted runner = 执行面回到客户网络，但控制面/推理仍出站到 Anthropic

### 事实锚点（已核实）
- CHANGELOG v2.1.224 新增：`claude self-hosted-runner`，让 Claude Code web/mobile/desktop sessions 运行在客户自有机器或容器上（Team/Enterprise）。
- self-hosted docs 明确三类对象：**Environment / Runner / Session**。
- 网络路径：runner/session 从客户网络 **outbound HTTPS 到 `api.anthropic.com`**；Anthropic **不 inbound 连接**客户网络。
- 重要限制：当前 public beta；启用需组织层面开关；ZDR / HIPAA BAA / 经 Bedrock、Vertex、Foundry、LLM gateway 推理 等场景需要逐项核实（docs 中列明限制，客户方案中不要默认承诺）。
- CHANGELOG 同时修复安全项：`denyRead: "[已移除本地路径]"` 这类尾斜杠 deny 条目在 Linux/macOS 可被绕过的问题；sandbox violation 细节现在会出现在 Bash tool results。

### SA 技术问答话术
> “Self-hosted environments 不是把模型也私有化。它把 **代码 checkout、构建、工具执行、secrets 访问** 放回客户控制的 runner；但 Anthropic 的控制面/推理/事件流仍通过 outbound 到 `api.anthropic.com`。所以它解决的是执行面与私网访问问题，不等同于 Azure 私有模型部署或数据完全不出境。”

### POC 最小清单
1. 组织启用 self-hosted environments（Team/Enterprise，public beta）。
2. 部署 runner：VM/容器均可；只开 outbound；不开放 inbound。
3. 验证三条边界：
   - runner 能访问内部 Git/包源/测试环境；
   - runner 能 outbound 到 `api.anthropic.com`；
   - session user/runner 绑定与容量隔离满足多用户要求。
4. 安全回归测试：[→harness]
   - `denyRead` 路径带/不带尾斜杠两组用例；
   - sandbox network deny 触发时，Bash result 是否暴露具体 deny reason；
   - cross-session `SendMessage` 在 bypassed permissions session 中是否需要人工批准。

### 架构图组件
```text
Developer / Claude Code UI
        |
        | control/event stream + inference (outbound HTTPS)
        v
api.anthropic.com  <----- outbound only -----  Self-hosted Runner (customer network)
                                                    |
                                                    +-- Session process A/B
                                                    +-- Internal Git / packages / test env
                                                    +-- Secrets store / CI cache
```

---

## 2. Codex 0.147.0 GA：插件目录、MCP 2026-07-28、自动审批与安全兜底同时到位

### 事实锚点（已核实）
- Codex release `rust-v0.147.0` 页面 200；npm registry `@openai/codex dist-tags.latest=0.147.0`，`alpha=0.148.0-alpha.2`。
- 0.147.0 release body 包含：
  - portable Agent Plugins + local/personal/workspace/remote plugin catalogs；
  - persistent/manual conversation sections；
  - `--approve-for-me` 自动审批；
  - Cursor-managed skills import；
  - opt-in MCP `2026-07-28` protocol（paginated discovery、MRTR、non-blocking server startup）；
  - bearer token/commands/history redaction；
  - 陌生项目 explicit trust；
  - 插件策略失败时 deny network（安全兜底）。

### SA 技术问答话术
> “Codex 0.147.0 是从 0.146.x 到插件治理层的一个生产基线跳跃。客户 POC 里可以开始讨论插件目录/远程目录/skills import，但 `--approve-for-me` 不能被解释成‘无人监管可生产放行’，应配合项目 trust、network-deny fallback、secrets redaction 与审计日志。”

### POC 最小清单
1. 版本基线：生产/客户演示优先锁 `latest=0.147.0`；`0.148.0-alpha.*` 只做观察。
2. 插件治理：
   - 明确 local/personal/workspace/remote catalog 哪些允许；
   - 插件安装来源与 SHA/版本锁定；
   - 策略解析失败时是否默认 deny network。
3. MCP 迁移：若客户 MCP server 仍是旧协议，需要用 2026-07-28 checklist 检查 paginated discovery / MRTR / startup 行为。
4. 自动审批：[→harness]
   - 将 `--approve-for-me` 纳入红队用例，不允许在敏感 repo 默认启用；
   - 验证 bearer token 是否在命令展示与 replay history 中脱敏。

---

## 3. Azure AI Agent + Semantic Kernel：MCP tool approval callback 的 fail-closed 语义

### 事实锚点（已核实）
- SK PR#14210 diff 中新增 `MCPToolApprovalCallback` / `MCPToolApprovalRequest` 导出。
- 示例注释写明：当 `mcp_tool.set_approval_mode("always")` 时，Semantic Kernel 会在每次 MCP tool call 前询问 agent 上配置的 `mcp_tool_approval_callback`；**若未配置 callback，则拒绝调用**。
- `MCPToolApprovalRequest` 字段包括 agent/thread/run/tool_call/server_label/function_name/arguments 等上下文（来自 diff 片段，完整类型需在正式 release 源码中复核）。

### SA 技术问答话术
> “这不是简单的 UI 弹窗，而是把 MCP tool call 的 human-in-the-loop 审批点放进 Agent 运行时。关键是 fail-closed：一旦要求 always approval 但没有 callback，调用应被拒绝而不是静默放行。”

### POC 最小清单
1. 配置一个高风险 MCP tool（如写库/调用外部系统）。
2. `approval_mode=always`，先不配 callback，确认 tool call 被拒绝。
3. 配 callback：
   - function_name/arguments 写入审计；
   - 低风险自动 allow；高风险要求人工确认；
   - 拒绝路径返回可诊断错误。
4. 架构图控制点：
```text
Azure AI Agent Run
   -> MCP Tool Call Requested
      -> SK mcp_tool_approval_callback
         -> Policy / Human Approval / Audit
            -> submit approval OR denial
```

---

## 4. AI Gateway + Purview DLP：把内容治理放在 APIM 网关层，而不是每个应用单独写

### 事实锚点（已核实）
- Azure-Samples/AI-Gateway PR#390 新增 `labs/apim-purview-dlp/README.MD` 与 `images/apim-purview-dlp.png`。
- README frontmatter：`Microsoft Purview DLP at the AI Gateway`；services 包含 Microsoft Purview、Azure API Management、Microsoft Foundry、Amazon Bedrock。
- 设计说明：APIM 同时代理 Foundry `gpt-4.1` 与 Amazon Bedrock Nova；在 prompt 上游（Gate 1）与 response 下游（Gate 3）调用 Microsoft Graph `dataSecurityAndGovernance/processContent`；后端不看到用户 token；Log Analytics 汇总模型与 Purview PAYG 成本。

### SA 技术问答话术
> “如果客户有多个模型后端（Foundry + Bedrock + 其他），DLP/审计不应散落到每个应用里。APIM 网关层用 Purview 做统一入站/出站 gate，后端只看到已治理后的请求，适合多模型、多业务线的企业治理方案。”

### POC 最小清单
1. APIM 作为统一 AI Gateway。
2. Entra app delegated permissions：`Content.Process.User`、`ProtectionScopes.Compute.User`、`ContentActivity.Write`（来自 PR diff 注释；生产前需按最新 Graph 文档复核）。
3. 两个 gate：
   - Gate 1：prompt 进入模型前 DLP；
   - Gate 3：model response 返回用户前 DLP。
4. 两个后端：Foundry + Bedrock；统一 Log Analytics 成本/审计查询。
5. 架构图组件：
```text
User/App
  -> APIM AI Gateway
      -> OBO Graph token (per turn, cached)
      -> Purview processContent Gate 1 (prompt)
      -> Foundry or Bedrock backend
      -> Purview processContent Gate 3 (response)
      -> Log Analytics cost/audit
```

---


| 候选 | 已知信号 | 为什么留后续 |
|---|---|---|
| `anthropics/skills` | 官方 Agent Skills repo，含 `skills/`、`spec/`、`template/`，无 GitHub releases | 适合套 `harvest-upstream-skills` 漏斗法，对比 Google skills / DeepMind science-skills / mattpocock / addyosmani |
| `langfuse/skills` | Langfuse 官方 tracing / prompt management / evaluation skills，小而官方 | 适合做 Agent observability/evals POC 的 skill-pack 示例 |
| `google/ax` | 分布式 agent runtime，v0.2.x 中有 workdir/path traversal 等安全修复信号 | 适合画“resumable distributed harness”架构图，但需源码级核实 |
| `openai/tunnel-client v0.0.11` | Secure MCP Tunnel 稳定版，含 GHCR 镜像、SBOM/provenance 线索 | 私有 MCP 接入 ChatGPT/Codex/Responses/AgentKit 的架构图候选 |
| `Azure-Samples/AI-Gateway PR#390` | 本资产仅从 diff/README 级提炼 | 若要客户演示，使用前需读 notebook/policy/Bicep 逐项参数 |

---

## 6. 直接反哺 harness workshop 的条目

- [→harness] Claude Code self-hosted runner：做“控制面 vs 执行面”架构图与红队用例（denyRead trailing slash、sandbox deny reason、cross-session SendMessage approval）。
- [→harness] Codex 0.147.0：新增“插件目录治理 + automatic approval 红队 + bearer token replay 脱敏”实验。
- [→harness] SK MCP approval callback：新增“fail-closed HITL tool approval”实验，用 callback 缺失时拒绝来验证默认安全性。
- [→harness] APIM + Purview DLP：新增“网关层双向内容治理”Azure POC 模块，可与 MCP OAuth/PRM lab 并列为 AI Gateway 安全章节。

## 7. Fail-loud

- `MCPToolApprovalRequest` 的完整字段与最终包版本兼容性仅从 PR diff 抽取；生产迁移前需读取正式 release 源码/文档。
- APIM Purview DLP 的 Graph 权限名来自 PR diff 注释；正式客户方案需按 Microsoft Graph/Purview 最新文档复核。
- `anthropics/skills`、`langfuse/skills` 只做 URL/README 级初筛，未审计 license、skill 质量、脚本安全性；不可直接建议客户安装。
- GitHub trending 候选 star/fork 多来自 HTML 解析，受 API 限流影响，未核实 created_at；刷量判断只作初筛，不作客户结论。
