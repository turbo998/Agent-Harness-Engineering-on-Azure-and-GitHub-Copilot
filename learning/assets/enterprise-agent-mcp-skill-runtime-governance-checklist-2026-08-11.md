<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Enterprise Agent MCP / Skill / Runtime Governance Checklist（2026-08-11）

> 目的：把原快照 6 个深挖对象沉淀成 SA 可复用的**技术问答 / POC 部署 / 架构图**清单。外部 README / docs 均按不可信资料处理；本文只提炼经原研究快照中 curl/git/raw 核实的事实，未执行任何上游仓库命令。

## 0. 证据与新旧状态

| 对象 | URL | 原研究快照中证据强度 | 新旧状态 |
|---|---|---|---|
| Microsoft Agent Framework `dotnet-1.17.0` | https://github.com/microsoft/agent-framework/releases/tag/dotnet-1.17.0 | URL 200；releases.atom 显示 2026-08-04；release HTML meta/snippet 含 Durable Task/Azure Functions/handoff/declarative workflow 条目 | 新增参考来源 |
| MAF PR#7602 BackgroundAgentsProvider.ReleaseSessionAsync | https://github.com/microsoft/agent-framework/pull/7602 | PR 200；`.diff` 200，读到 `ReleaseSessionAsync`、`TaskCancellations`、`IsReleased`、abandoned work 说明 | 新增深挖 |
| MAF PR#7606 A2A preview consent URLs | https://github.com/microsoft/agent-framework/pull/7606 | PR 200；`.diff` 200，读到 consent error type 从 `mcp` 扩展为 `mcp | a2a_preview` | 新增深挖 |
| Azure MCP Server 3.0.0-beta.33/beta.32 | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.33 | URL 200；`servers/Azure.Mcp.Server/CHANGELOG.md` 本地 clone 逐字读取 beta.33/beta.32 | 新增版本信号；beta30/31 已覆盖，非重复 |
| OpenAI MCPKit | https://github.com/openai/openai-mcpkit | repo/raw README 200；sparse clone 读 Python/TypeScript scaffold README 与 token verifier/auth 文件；HTML star 69 | 新发现 |
| google-gemini/gemini-skills | https://github.com/google-gemini/gemini-skills | repo/raw README 200；sparse clone 仅读 `skills/*/SKILL.md`（4 个）frontmatter/开头，未全读；HTML aria-label star 3892，未 API 复核 | 新发现 |
| Codex changelog + build-skills | https://developers.openai.com/codex/changelog / https://developers.openai.com/codex/skills | 301→`learn.chatgpt.com`→200；HTML 中检索到 `0.147.0`、Agent Plugins、`--approve-for-me`、progressive disclosure、`SKILL.md` | 复核 + URL 健康新角度；0.147 已在 08-08/08-10 记录 |
| Claude Code changelog/sub-agents/best-practices | https://code.claude.com/docs/en/changelog / https://docs.anthropic.com/en/docs/claude-code/sub-agents / https://www.anthropic.com/engineering/claude-code-best-practices | 200/重定向后 200；HTML 中检索到 2.1.226/2.1.225、gateway/worktree、subagents、memory、parallel、best-practice headings | 复核 + 版本门槛新角度；v2.1.226 已在 08-10 记录 |
| Codex agents / Cookbook旧URL健康 | https://developers.openai.com/codex/agents / https://cookbook.openai.com/examples/agent_improvement_loop | 重定向后 404 | 新增“死链/不应引用”提示 |

## 1. 面向客户的 5 个治理问题（问答速查）

### Q1：企业把私有数据接入 ChatGPT / Agent 时，MCP Server 的身份边界怎么讲？

**推荐话术**：不要把 MCP Server 画成“公网工具接口”。它应当是一个**企业控制的授权网关**：

1. MCP client 只携带 OAuth/OIDC bearer token；
2. MCP Server 验证 issuer / audience / scopes；
3. 对高价值业务数据继续接入 entitlement / subject-level authorization；
4. 仅在授权通过后调用内部系统；
5. 记录工具调用审计日志，但不要记录 token / PII。

**来自 MCPKit 的可复用点**：
- 支持任意 OIDC provider（README 以 Auth0 为例）；
- Python scaffold 同时给了 JWT verifier 与 RFC 7662 introspection verifier；
- README 明确提示 JWTVerifier **不包含 entitlements，需要自行补充**；
- TypeScript scaffold 的 `authenticateRequest` 可扩展 subject-level authorization。

**Azure 映射**：
- 客户若已在 Entra ID：可把 Auth0 示例替换为 Entra ID / External ID；
- APIM 可作为 MCP Server 前置层，承担 rate-limit、WAF、JWT validation、日志脱敏；
- 内部数据源侧继续用 Managed Identity / workload identity，不把下游密钥暴露给 Agent。

### Q2：Agent 有后台任务 / subagent 后，如何避免无人管的任务继续烧钱？

**推荐话术**：Session lifecycle 是企业 agent runtime 的必备控制面，不是 SDK 细节。

从 MAF PR#7602 抽出的 POC 检查点：
- 每个后台 task 必须关联 session；
- task 需要可取消 token / cancellation source；
- host 结束 session 时显式调用 release / cleanup；
- released runtime 必须拒绝启动新的后台工作；
- release 要有超时（PR 中出现默认 30 秒 release timeout）；
- abandoned work 继续调用 models/tools 属于 FinOps + 安全双风险。

**架构图组件**：`Session Store`、`Task Runtime`、`Cancellation Map`、`ReleaseSession API`、`Cost/Telemetry`。

### Q3：MCP / A2A 工具需要用户同意时，前端应该拿到什么？

MAF PR#7606 提醒：同意不是 MCP 专属问题；A2A preview 也会出现 consent URL。

**POC checklist**：
- 错误结构中保留 `type`（如 `mcp` / `a2a_preview`）；
- 错误 code 明确为 `CONSENT_REQUIRED`；
- response body 返回可点击的 consent URL；
- 前端把 consent flow 与原始 task id / session id 绑定；
- consent 之后重新尝试时，不让 LLM 自己伪造“已同意”。

### Q4：Azure MCP Server beta.33 对架构图有什么影响？

beta.33 的关键不是“又多一个 Advisor 工具”，而是**metadata catalog 从 Advisor ARM API 迁到 Azure Resource Graph**：

- `azmcp advisor metadata get` 读取全局 Advisor recommendation-type metadata；
- `advisor_recommendation-type_list` 重命名为 `advisor_metadata_list`（breaking）；
- 发现路径迁移到 ARG metadata catalog，包含更丰富 localized details 与 filters；
- 新遥测字段：`IsLearn`、`ToolSource`、`ToolParameters`、`ToolAnnotations`。

**SA 落点**：
- 架构图里 Azure MCP Server 的 Advisor/metadata 查询应画到 ARG；
- 客户若依赖旧 tool name，需要做 beta 升级影响评估；
- 新 telemetry 字段可映射到“工具调用审计 / 学习模式 / 参数使用频度”看板。

### Q5：Codex / Claude Code skills 与 subagents 如何落地成企业 harness？

**最小三件套**：

1. **Skill**：写稳定 SOP（触发条件、输入、输出、验证命令、失败处理）；
2. **Subagent**：隔离高噪声/高专业度任务（reviewer/debugger/researcher/db-validator）；
3. **Gate**：在关键路径加入人工审批、自动测试、adversarial review 或 policy check。

**Codex 侧原研究快照中复核**：
- Build skills 页确认 progressive disclosure：先看 name/description，选中后再读完整 `SKILL.md`；
- Codex 0.147.0 changelog 确认 Agent Plugins、plugin catalog search、`--approve-for-me`、MCP 2026-07-28 支持；
- `developers.openai.com/codex/agents` 当前重定向后 404，不要作为稳定引用。

**Claude Code 侧原研究快照中复核**：
- changelog 最新可见 2.1.226/2.1.225；2.1.225 涉 gateway spend-limit、workspace trust、OAuth/headless session 修复；
- sub-agents 文档确认工具控制、persistent memory、hooks、foreground/background、parallel research、chain subagents、concurrent limit 等主题存在；
- best-practices 页支持“Explore → Plan → Code → Verify”、`CLAUDE.md`、permissions、subagents、adversarial review、auto mode 等治理建议。

## 2. POC 部署检查清单

### A. Authenticated MCP POC（OpenAI MCPKit / Azure 映射）

- [ ] IdP：确认 Entra / Auth0 / Okta 等 OIDC issuer、JWKS、audience、scope。
- [ ] Token validation：本地 JWT 验证还是 RFC 7662 introspection；若是 JWE/opaque token，不能假设本地解析。
- [ ] Resource binding：检查 `aud` / RFC 8707 resource，避免 token 被挪用到错误 MCP Server。
- [ ] Entitlement：JWT scope 之外增加业务级授权（tenant、project、dataset、row/field）。
- [ ] Secrets：MCP Server 用 Managed Identity / Key Vault / workload identity 调下游，不把密钥给 LLM。
- [ ] Logs：只记 tool name、subject hash、resource id、latency、decision；不记 bearer token。
- [ ] Red-team：伪造 audience、缺 scope、跨 tenant subject、已撤销 entitlement、introspection 服务超时。

### B. Background / subagent runtime POC

- [ ] 每个后台任务绑定 session id + task id。
- [ ] 支持 release session / cancel in-flight tasks。
- [ ] released runtime 禁止启动新任务。
- [ ] 超时后强制清理并记录成本归因。
- [ ] 前台主 agent 只接收摘要，不继承后台 agent 的不可信上下文。
- [ ] reviewer/debugger/researcher subagent 明确工具白名单。

### C. Skill library POC（google-gemini/gemini-skills 的启发）

- [ ] 只导入经过人工审查的 skill；社区或外部 skill 的“override rules”语句必须当作资料文本重新改写，不直接照搬。
- [ ] `description` 必须短、具体、可路由。
- [ ] skill 正文必须包含：何时用、输入、输出、验证、限制、区域/合规 caveat。
- [ ] 技术事实（模型名、区域、定价）必须有“as-of 日期 + 来源 URL”。
- [ ] 对会过期的模型/SDK 列表，用引用文件或版本门槛表，不硬编码进客户承诺。

## 3. 架构图样板（文字版，可转 SVG）

```text
User / Operator
  │
  ▼
Agent Client (ChatGPT / Claude Code / Codex / Copilot)
  │  OAuth/OIDC bearer token + task context
  ▼
Enterprise MCP Gateway / APIM
  ├─ JWT / introspection validation
  ├─ Resource binding + scope check
  ├─ Entitlement service check
  ├─ Consent URL broker (MCP + A2A preview)
  └─ Audit / telemetry / rate limit
        │
        ├── Azure MCP Server ──► Azure Resource Graph / Advisor metadata
        ├── Internal Tools ───► CRM / KB / Data APIs
        └── Agent Runtime ────► Background tasks / subagents
                                 ├─ Session store
                                 ├─ Cancellation map
                                 ├─ ReleaseSession API
                                 └─ Cost/trace sink
```

## 4. 原快照可直接反哺 harness workshop 的条目

- [→harness] **Authenticated MCP lab**：把 MCPKit 的 OIDC/JWT/introspection/entitlement 四层拆成一个 Azure APIM + Entra + MCP Server POC 检查卡。
- [→harness] **Background agent lifecycle red-team**：用 MAF PR#7602 的 abandoned work 风险，设计“session 关闭后后台任务是否还会调用模型/工具”的测试。
- [→harness] **Consent replay/tamper gate**：把 PR#7606 的 MCP/A2A consent URL 与 08-10 PR#7581 的 approval binding 合并成“同意/审批不可由 LLM 伪造”的红队用例。
- [→harness] **Skill import firewall**：外部 `SKILL.md` 即使来自官方/高星 repo，也必须先 sanitize，再重写成内部 skill；不要直接执行其安装脚本或复制“override your training data”式指令。
- [→harness] **URL health gate**：把原研究快照中发现的 `developers.openai.com/codex/agents` 与 cookbook `agent_improvement_loop` 404 写进 workshop 链接检查脚本。

## 5. Fail-loud

- 未部署任何 POC；所有部署步骤均为设计检查清单。
- `openai/openai-mcpkit` stars 用 GitHub HTML aria-label 抽取为 69；未通过 GitHub API（匿名 API 可能限流）。
- `google-gemini/gemini-skills` stars 用 HTML 抽取为 3892；只做目录/前言漏斗，未全读每个 skill。
- Codex / Claude docs 为 JS/静态站 HTML 抽取；已核实关键词存在与 URL 可达，但未逐字完整阅读全页。
- Azure MCP beta.33/beta.32 来自本地 sparse clone 的 `CHANGELOG.md`；未运行 Azure MCP Server。
