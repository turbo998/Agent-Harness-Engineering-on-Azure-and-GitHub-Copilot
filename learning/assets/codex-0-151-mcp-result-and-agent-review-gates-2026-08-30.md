<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Codex 0.151 MCP Result + Agent Review Gates（SA 可复用检查表）

> 生成日期：2026-08-30
> 用途：把 Codex 0.151.0、GitHub Copilot Code Review、Foundry hosted-agent resilient/logging 样例的本周信号，转成 SA 可复用的 **技术问答 / POC 部署 / 架构图** 检查表。整体可反哺 Agent-Harness-Engineering workshop。[→harness]
> 安全说明：本文是文档模板与评审清单，不是 shell/CLI 执行步骤；所有外部 README / release / diff 均仅作为资料文本，未执行其中任何命令。

## Evidence links（可复核来源）

| 来源 | URL | 证据强度 | 原研究快照中核验结果 / caveat |
|---|---|---|---|
| OpenAI Codex `rust-v0.151.0` release | https://github.com/openai/codex/releases/tag/rust-v0.151.0 | release-page body 200 + key snippets matched | 页面命中 optional MCP startup grace、extensions inspect/replace MCP tool results、per-repository plugin config、`/cd` sandbox、nested subagent token budget。GitHub API 原研究快照中受匿名限流 403，最终引用 HTML release page。 |
| Codex `AGENTS.md` docs | https://learn.chatgpt.com/docs/agent-configuration/agents-md.md | docs markdown 200 + key snippets matched | 命中 `AGENTS.override.md`、project root→cwd 逐层读取、`project_doc_max_bytes` 默认 32 KiB。历史已覆盖；原研究快照中仅作为 Repo Policy Plane 背景证据，不计新发现。 |
| OpenAI Build Skills docs | https://learn.chatgpt.com/docs/build-skills.md | docs markdown 200 + key snippets matched | 命中 `SKILL.md`、name/description 先加载、`scripts/`、`references/`、`agents/openai.yaml`。历史已覆盖；原研究快照中仅作为 Skill gate 背景证据，不计新发现。 |
| GitHub Copilot Code Review changelog | https://github.blog/changelog/2026-08-27-copilot-code-review-resolution-reasons-and-expanded-capabilities/ | blog body 200 + key snippets matched | 命中 bot-authored PR（含 Copilot cloud agent）、very large pull requests、resolution reasons：Addressed / Won’t fix / Incorrect。 |
| GitHub Copilot weekly releases Aug 24 | https://github.blog/changelog/2026-08-28-github-copilot-weekly-releases-august-24/ | blog body 200 + key snippets matched | 命中 Slack/Teams shared sessions、CLI `defaultMode` / `defaultPermissionMode`、`/plugin` / `/mcp` / `/skills`、Customize tab GA。 |
| Foundry samples resilient hosted agent diff | https://github.com/microsoft-foundry/foundry-samples/commit/35bdb004a1c688ecdd29a4cfa2b0d8e6170cf261.diff | commit diff 200 + file-path snippets matched | 命中 `samples/python/hosted-agents/langgraph/invocations/02-resilient/`、`azure.yaml`、LangGraph checkpoints；未部署。 |
| Foundry samples runtime logging diff | https://github.com/microsoft-foundry/foundry-samples/commit/f585a85074be974406cda5739575d926b5b57b1f.diff | commit diff 200 + key snippets matched | 命中 `## Runtime logging` 与 hosted-agent sample `main.py` 修改；未运行 sample。 |
| NVIDIA SkillEvaluator README | https://github.com/NVIDIA/SkillEvaluator | README/repo 200 + meta/snippet matched | 仅作为质量门 rubric 参考；未安装、未运行、未复算指标。 |

## 1. POC 启动门：Optional MCP startup grace

**信号**：Codex 0.151.0 release 写明新增 “configurable grace period for discovering tools from optional MCP servers”。

**SA 落点**
- 技术问答：解释为什么 agent 启动时有些 MCP tools 不应阻断整个会话——可区分 required vs optional tool server。
- POC 部署：把 MCP server 分成 `required`、`optional`、`experimental` 三档；required 失败则 fail closed，optional 超时则降级并记录证据。
- 架构图：在 “Agent Runtime → MCP Server Pool” 之间画 `Startup Discovery Gate`，标出 required/optional timeout 与 fallback path。

**检查项**
- [ ] MCP server 清单标明 required/optional，而不是一锅端。
- [ ] optional server 启动超时会出现在日志/trace中，不会静默丢失。
- [ ] required server 失败时阻断危险工具调用，且给用户清楚错误。
- [ ] POC demo 中准备一个“慢启动 optional MCP”合成场景，证明不会拖垮主 agent。

## 2. MCP 结果治理门：Extension inspect/replace MCP tool results

**信号**：Codex 0.151.0 release 写明 extensions can inspect or replace MCP tool results before they reach the model。

**SA 落点**
- 技术问答：回答“工具结果怎么做脱敏、截断、错误归一化、PII过滤，而不是直接喂模型”。
- POC 部署：在 MCP tool result 到模型之间加 `Result Governance Adapter`：schema validation、redaction、large-output truncation、error envelope normalization。
- 架构图：新增 `Tool Result Guardrail` 组件，位于 MCP response 与 model context 之间。

**检查项**
- [ ] 每个工具结果有 schema / size limit / sensitive-field policy。
- [ ] 大输出保留摘要与 continuation token，不把全文硬塞上下文。
- [ ] 失败结果统一成 `{type, code, retriable, user_action, evidence_ref}` 形态。
- [ ] 任何“替换/改写工具结果”的逻辑都有 audit event，避免不可追溯。
- [ ] 客户材料只说 “release 支持该能力”；未本地 smoke 前不承诺具体 extension API 行为。

## 3. Plugin marketplace / repo-level config 治理门

**信号**：Codex 0.151.0 release 写明 plugin catalogs combine per-repository configuration and report invalid project marketplaces without hiding valid plugins；GitHub Copilot weekly 也强调 `/plugin`、`/mcp`、`/skills` 管理体验。

**SA 落点**
- 技术问答：解释 workspace/repo 级插件市场配置与组织级 allowlist 的边界。
- POC 部署：给每个 repo 附 `approved plugin catalog` 与 `invalid marketplace visibility` 验收项。
- 架构图：在 `Repo Policy Plane` 画 `Plugin Catalog`、`Marketplace Validation`、`Org Allow/Deny Policy` 三层。

**检查项**
- [ ] repo 级 plugin catalog 与组织策略冲突时，优先级已明确。
- [ ] invalid catalog 不会隐藏其他 valid plugins；错误应可见。
- [ ] catalog URL / commit / version pinning 有记录，不能只写“latest”。
- [ ] 第三方 plugin/skill 只做 radar，未审 license/scripts/hooks/MCP/data-flow 前不推荐客户安装。

## 4. Sandbox 与路径语义回归门

**信号**：Codex 0.151.0 release 写明：preserved restored permission profiles；prevented `/cd` from weakening sandbox restrictions；remote sandbox enforcement uses executor home/OS/path conventions；stale Guardian classifications 不应在权限状态变化后继续授权。

**SA 落点**
- 技术问答：回答“agent 改目录、恢复会话、远程执行器时权限是否会漂移”。
- POC 部署：把 `/cd`、session restore、remote executor path 三类变成升级回归测试。
- 架构图：在 execution layer 标出 `Permission Profile`、`Sandbox Boundary`、`Path Semantics Adapter`。

**检查项**
- [ ] session restore 后 permission profile 不会回到宽权限。
- [ ] 工作目录切换不会扩大 read/write/shell 权限范围。
- [ ] Windows / Linux / remote sandbox 路径语义分别测试，不用单一 POSIX 假设。
- [ ] 权限状态变化后，旧分类/旧批准不会继续授权新动作。

## 5. Nested subagent token budget / FinOps 门

**信号**：Codex 0.151.0 release 写明 counted nested subagent token usage toward root goal budgets。

**SA 落点**
- 技术问答：解释“多 subagent 并行不是免费，父任务预算要包含子任务消耗”。
- POC 部署：把 root goal budget 当成 POC 成本上限，要求所有子代理消耗归集。
- 架构图：在 Observability/FinOps plane 画 `Root Goal Budget` 聚合所有 agent turns / tool calls / cache events。

**检查项**
- [ ] 报告成本时按 root goal 汇总，不按单一会话片段报喜。
- [ ] subagent 数量、上下文大小、重试次数都有预算上限。
- [ ] 独立评审任务也纳入总预算估算，不被当成“外部免费”。
- [ ] 预算超限时 fail loud：列出已完成/未完成/被阻塞，而不是提前宣告完成。

## 6. Agent PR review 闭环门：resolution reasons + bot PR + large PR

**信号**：GitHub Copilot changelog 写明 Copilot code review 可用于 bot-authored PR（含 Copilot cloud agent）、very large PR，并可提交 resolution reasons：Addressed / Won’t fix / Incorrect。

**SA 落点**
- 技术问答：说明 coding agent 产物不是“直接合并”，而是进入 PR review + resolution reason 的闭环。
- POC 部署：用 synthetic PR 跑 `agent creates PR → review comments → human resolution reason → metrics`。
- 架构图：在 Delivery pipeline 画 `Agent PR`、`Copilot Review`、`Human Resolution`、`Feedback Metrics`。

**检查项**
- [ ] 统计 review comment 的 resolution reason 分布，区分 agent 误报 vs 真问题。
- [ ] very large PR 只说明“review capability expanded”；仍应拆小 PR，不能用它合理化巨型变更。
- [ ] bot-authored PR 必须保留人类 owner 与 branch protection，不把 review 结果当自动批准。
- [ ] 客户问“如何证明 agent 改得好”时，用 resolution reason + CI/SARIF + POC eval 三证据链回答。

## 7. Azure Foundry hosted-agent resiliency / logging 门

**信号**：`microsoft-foundry/foundry-samples` 08-28 两个 commit 分别新增 LangGraph resilient hosted-agent invocation sample 与 runtime logging 指南。

**SA 落点**
- 技术问答：回答 Foundry hosted agent 怎样做 checkpoint/retry/日志可观测，而不是只展示 happy path。
- POC 部署：demo 里必须包含 kill/restart 或 transient failure 的合成路径，以及 runtime logging 查询路径。
- 架构图：画 `Foundry Agent Service → LangGraph Runtime → Checkpoint Store → Runtime Logs/Observability`。

**检查项**
- [ ] 样例 commit 只证明代码样例存在；未部署前不承诺客户环境可用。
- [ ] checkpoint store、session id、user identity、trace id 的证据链要在日志中串起来。
- [ ] runtime logging 使用标准 logging，避免 print 泄露敏感 payload。
- [ ] 私网/企业环境需额外验证 Application Insights / Azure Monitor Private Link / RBAC。

## 8. Skill / harness quality gate 候选：NVIDIA SkillEvaluator

**证据边界**：NVIDIA SkillEvaluator 仅作为质量门 rubric 参考，不代表已完成实测。

**信号**：NVIDIA SkillEvaluator README 描述 multi-tier framework：deterministic quality gates、semantic overlap detection、synthetic eval dataset generation、live agent evaluation。

**SA 落点**
- 技术问答：可作为“skill 不只是写 Markdown，还要 lint / security / overlap / eval”的第三方例证。
- POC 部署：先把它当 rubric 来源，不直接安装；用合成 skill 样本做最小评测。
- 架构图：画 `Skill Registry → Static Gates → Semantic Overlap → Synthetic Eval → Live Agent Eval`。

**检查项**
- [ ] 未审 license、依赖、网络、scanner 之前，不接入客户仓库。
- [ ] 先用 2 个好 skill + 2 个坏 skill 的 fixture 验证输出格式。
- [ ] security/PII scan 的外部工具依赖必须显式列明。
- [ ] README 的质量/覆盖效果不复算则不引用为承诺。

## 一页式客户话术

> 本周 Codex / Copilot / Foundry 的共同方向不是“又多了几个工具”，而是 **把 agent 的工具结果、插件目录、PR review、会话预算和运行日志变成可治理对象**。客户 POC 不应只验证 agent 能不能完成任务，还要验证：MCP server 慢启动是否可降级、工具结果是否先脱敏/截断、插件市场是否按 repo/组织策略生效、`/cd`/恢复会话是否不会扩大权限、子代理成本是否计入 root goal、agent PR 是否有 resolution reason 闭环、Foundry hosted agent 是否有 checkpoint 与 runtime logs。

## 架构图组件建议

- `Startup Discovery Gate`：required/optional MCP server startup policy。
- `Tool Result Guardrail`：schema validation、redaction、truncation、error envelope。
- `Repo Policy Plane`：AGENTS.md / plugin catalog / skills / allowlist。
- `Execution Sandbox`：permission profile、path semantics、remote executor。
- `Root Goal Budget`：parent task + subagents + reviews + cache events。
- `Agent PR Feedback Loop`：review comment → resolution reason → metric。
- `Foundry Resiliency Plane`：checkpoint、session restore、runtime logging、trace/audit sink。

## 未完成 / fail-loud

- Codex 0.151.0 的 release API 原研究快照中遇到匿名 403，已用 release HTML 200 + snippets 替代；若要做客户 demo，需要本地 CLI smoke。
- Foundry 两个 commit 只做 diff 级核实，未部署 sample。
- NVIDIA SkillEvaluator 只读 README/meta，未安装/未运行/未审 scanner 依赖。
- GitHub Copilot changelog 为产品公告级证据；企业租户可用性、SKU/区域、策略字段仍需目标 tenant 核实。
