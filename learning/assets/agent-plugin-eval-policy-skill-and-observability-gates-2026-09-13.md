<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent plugin eval / policy skill / observability gates — SA reusable checklist (2026-09-13)

> **用途**：把原快照中验证到的 Claude Code `plugin eval`、OpenAI Cookbook Agents API policy-skill 样板、Codex AGENTS.md/SDK 事件语义、Azure MCP beta.43 与 Copilot 指标更新，沉淀成 SA 日常可复用的三件套：客户技术问答速答、POC 验收门、架构图组件。
>
> **安全说明**：本文中的命令形态、CLI 名称和配置字段均作为上游文档/源码证据或设计参考，不是直接执行指令。任何客户 POC 前必须在一次性测试仓库/测试订阅/无真实 secret 的环境中验证。
>
> **证据边界**：所有链接 2026-09-13 原快照中 HTTP 200（仅代表原快照当时可达，不代表本次已重验） 核实；除明确说明外，未安装/运行 Claude Code、Codex、Azure MCP、OpenAI Agents API 示例，也未连接真实 Azure/OpenAI/Anthropic 租户。

## 1. Evidence links（可复现来源）

| 主题 | URL | 原快照中证据层级 | 已核实关键字/事实 | 边界 |
|---|---|---|---|---|
| Azure MCP Server beta.43 | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.43 | release page 200 + raw CHANGELOG 200 | `3.0.0-beta.43 (2026-09-10)`、Azure IoT Operations toolset、Backup richer state / vault managed identity details | 未安装包；未连 Azure；未读全部 schema |
| Azure MCP CHANGELOG | https://raw.githubusercontent.com/microsoft/mcp/main/servers/Azure.Mcp.Server/CHANGELOG.md | raw file 200 | `iotoperations instance list/get`、`azurebackup protecteditem get`、vault managed identity details | command-shaped names are evidence snippets only |
| Copilot VS Code Agent metrics | https://github.blog/changelog/2026-09-11-add-vs-code-agents-to-copilot-usage-metrics/ | GitHub Changelog HTML 200 + body keywords | `daily_active_vscode_agent_users`、`used_vscode_agent`、`totals_by_vscode_agent` | 未调用企业 metrics API |
| Copilot code review updates | https://github.blog/changelog/2026-09-11-auto-resolution-and-analysis-updates-in-copilot-code-review/ | GitHub Changelog HTML 200 + body keywords | Copilot code review uses shell tools behind Copilot agent firewall; Lite reviews use an ensemble | 未核 credits / repo policy 交互 |
| Claude Code changelog 2.1.269 | https://code.claude.com/docs/en/changelog.md | markdown 200 | `claude plugin eval`、`/output-style`、Bash edit diff、OTEL repo attrs、Workflow concurrency env var | 未 CLI smoke；2.1.270 npm next 仅 radar |
| Claude plugin eval docs | https://code.claude.com/docs/en/plugin-evals.md | markdown 200 | no-plugin baseline、grader、JSON+HTML report、CI gate、`tool_used: Skill` failure diagnosis | 只读文档，未生成 eval |
| Codex changelog | https://learn.chatgpt.com/docs/changelog | rendered markdown scrape / HTML 200 | Codex CLI Python SDK 0.154.0: `ExternalMessage`、`include_turns`、`turn_service_tier`、source metadata；CLI 0.154.0 worktree / inline questions | `.md` 直接 404，正文通过页面渲染/抓取取得；未运行 SDK |
| Codex AGENTS.md docs | https://learn.chatgpt.com/docs/agent-configuration/agents-md.md | markdown 200 | `AGENTS.override.md` global/project priority、`CODEX_HOME`、fallback filenames、`project_doc_max_bytes` 32 KiB | 旧源新角度，非首次发现 |
| OpenAI Cookbook Agents API commit | https://github.com/openai/openai-cookbook/commit/6e43b29 | commit page 200 | “Add Agents API apps and sandbox examples” | 未读全 diff；raw README/skill 已抽查 |
| Cookbook Agents API README | https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/agents_api/README.md | raw 200 | five applications + sandbox integrations; document reviewer uses policy skills and specialist agents | 未运行 Python 3.14/uv sample |
| Cookbook document-review README | https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/agents_api/apps/document_review/README.md | raw 200 | read-only input/policy mounts, output read-write; specialist subagents; restricted executor key | 示例模型/依赖未实测 |
| Cookbook policy skill | https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/agents_api/apps/document_review/skills/expense-review-policy/SKILL.md | raw 200 | policy ID `AP-104`、line-item extraction、`summary.json`、only coordinator writes summary、never approve payments/sign contracts/external actions | policy content是示例，不可直接用于客户财务流程 |

---

## 2. SA 技术问答速答（可转客户）

### Q1：Claude Code 的 plugin/skill 能不能像代码一样做回归测试？
**短答**：可以。官方 `plugin eval` 把“真实 prompt + 多个 grader + no-plugin baseline + JSON/HTML report + CI gate”做成官方可评测机制。SA 推荐把任何要进客户仓库的 skill/plugin 至少配两类 grader：
1. **结果 grader**：regex/LLM rubric，验证答案是否符合业务输出契约。
2. **行为 grader**：`tool_used` / `Skill` / `tool_order` / file existence，验证它有没有真的调用该 skill、有没有写对文件。

**POC 门槛**：第一次 Δ 接近 0 且 `tool_used: Skill` 失败时，不要怪模型；先修 `description` 路由契约，再重复默认三次运行确认，不要凭单次结果上线。

### Q2：Codex 的 `AGENTS.md` 指令冲突怎么排查？
**短答**：按官方发现链排：
- global：`CODEX_HOME`（默认 `~/.codex`）下 `AGENTS.override.md` 优先于 `AGENTS.md`；
- project：从 repo root 到当前目录逐层查 `AGENTS.override.md` → `AGENTS.md` → fallback filenames；
- merge：越靠近 cwd 的文件越晚拼接、语义上覆盖前文；默认总量 `project_doc_max_bytes=32KiB`。

**SA 落点**：客户抱怨“Codex 不听项目规范”时，先查 override / nested 文件 / 32KiB 截断，而不是直接改 prompt。这个模式可反哺 harness workshop 的“配置控制面排错”实验。

### Q3：OpenAI Cookbook 的 Agents API 样板对企业 POC 有什么新价值？
**短答**：它给出一个可讲清楚的“policy-as-skill + specialist subagents + sandbox provisioning”参考样板。Document reviewer 示例把输入/政策只读挂载、输出读写挂载、每文档 specialist subagent、coordinator 统一 `summary.json` 以及“永不批准付款/签合同/采取外部动作”写进 skill 约束。

**SA 落点**：这可作为合同/发票/合规文档审阅 POC 的参考骨架：业务政策=skill，文档处理=子代理，最终决策=人类审批，sandbox=隔离执行面；落地前需按客户政策、安全边界和执行环境重做验证。

### Q4：Copilot Agent 在企业采用率和代码审查上有什么新可观测点？
**短答**：GitHub Copilot metrics 现在把 VS Code Agents window 纳入企业/组织/用户粒度指标（`daily_active_vscode_agent_users`、`used_vscode_agent`、`totals_by_vscode_agent`）。同时 Copilot code review 宣布更深的 shell-tool 分析运行在 Copilot agent firewall 后，并在 Lite reviews 使用 agent ensemble。

**SA 落点**：企业汇报从“购买了多少 seat”升级到“Agent 窗口是否被真实使用、session/message 是否增长”；code review POC 则要把防火墙、credits、branch protection、required review 和 SARIF/CodeQL 结果串起来，不应把 Copilot 评论当作唯一质量门。

### Q5：Azure MCP beta.43 对架构/POC有什么提醒？
**短答**：beta.43 增加 Azure IoT Operations toolset，并让 Azure Backup protected item/vault 返回更丰富状态和 managed identity 信息。对 SA 来说，重点不是“又多几个工具”，而是 MCP tool 的领域覆盖进入 IoT/备份/身份状态面，POC 必须分清 read-only inventory、state inspection、mutating DR/backup operation 三类风险。

---

## 3. POC 验收门（可复制到方案文档）

| Gate | 最低通过标准 | 失败时优先排查 | 对应原快照中来源 |
|---|---|---|---|
| Skill/plugin routing gate | 自然语言 prompt 下 skill/tool_used grader 通过；with-plugin 分数高于 no-plugin baseline | `description` 是否过泛；skill 触发词是否只靠 slash/显式命令；是否缺真实业务 prompt | Claude plugin eval docs |
| Policy-as-skill gate | Skill 写明 policy ID、适用范围、禁止外部动作、输出 schema、角色写权限边界 | 政策是散文而非执行契约；缺 human approval；coordinator/specialist 都能写最终文件 | OpenAI Cookbook policy skill |
| Sandbox/provisioning gate | 明确 application-managed vs webhook-managed；删除 API session 不等于停止 provider compute；executor key 单独最小化 | 应用 key 进入 sandbox；compute cleanup 漏掉；provider handler 未鉴权 | Cookbook sandbox README |
| Agent observability gate | VS Code Agent adoption 指标、session/message、review activity、成本/credits 能被单独看见 | 只看 seat 激活率；指标没有区分 chat vs agent window；缺用户级/组织级分层 | GitHub Copilot metrics changelog |
| Tool firewall / review gate | Code review agent 的 shell tool 能力放在 firewall、CI、branch protection、required human review 之后 | 把 auto-resolution 当作自动 merge；缺审查责任边界；高风险 findings 没 human review | Copilot code review changelog |
| MCP cloud-control-plane gate | MCP tool 按 read/list/get、state inspection、mutating operation 分类；mutating 类需测试订阅、审批、审计、回滚 | 只按“工具数”估算风险；未审 schema/RBAC；未区分 IoT inventory 与备份/DR 变更 | Azure MCP beta.43 changelog |
| Codex config-debug gate | 记录 `CODEX_HOME`、global/project/nested override、fallback filenames、32KiB cap | stale instructions、override 遮蔽、嵌套目录误覆盖 | Codex AGENTS.md docs |
| Event/history gate | 对 late-joining handles / resumed turns 标注是否可能只收到部分事件；source metadata 入 trace | 把返回 response 当作完整模型上下文；attach after completion 未处理 | Codex Python SDK 0.154.0 changelog |

---

## 4. 架构图组件库（文字版，可转 Mermaid/Draw.io）

### 4.1 Plugin eval 回归门
```
Developer / SA
  -> Eval cases (real prompts)
  -> Claude plugin eval runner
       -> with plugin arm
       -> without plugin baseline arm
       -> graders: regex / tool_used / file_exists / LLM rubric / baseline delta
  -> JSON + HTML report
  -> CI threshold / release decision
```
**图上必须标注**：no-plugin baseline、默认多次运行、失败优先修 `description`，不要只画“plugin → Claude”。

### 4.2 Policy-as-skill document review
```
Human reviewer
  -> Review app / Agents API session
       -> mounted input docs (read-only)
       -> mounted policy skill (read-only)
       -> output folder (write)
       -> specialist subagents per document
       -> coordinator writes summary.json
  -> human approval / escalation
```
**图上必须标注**：policy-as-skill、specialist/coordinator 写权限边界、external action 禁止、sandbox/executor key 与 application key 分离。

### 4.3 Enterprise Copilot observability
```
Developers in VS Code Agents Window
  -> Copilot sessions/messages
  -> Enterprise/Org/User metrics API
       -> daily_active_vscode_agent_users
       -> used_vscode_agent
       -> totals_by_vscode_agent
  -> Adoption / ROI / training backlog dashboard
```
**图上必须标注**：Agent 窗口指标 ≠ 普通 chat 使用率；还要叠加 credits、policy、review/CI 结果。

### 4.4 Azure MCP risk zoning
```
Agent client
  -> MCP server (Azure.Mcp.Server beta.43)
       -> Read/list/get inventory tools (IoT Operations list/get)
       -> State inspection tools (Backup protected item / vault MI details)
       -> Mutating tools (must be separately reviewed)
  -> Azure RBAC / Managed Identity / audit logs / approval gate
```
**图上必须标注**：read-only inventory、state inspection、mutating operation 三色分区；不要用“工具数”替代风险分级。

---

## 5. [→harness] 可直接反哺 workshop 的练习卡

1. **Plugin eval ablation lab**：给一个 deliberately vague skill 描述，跑自然语言 case；先观察 `tool_used: Skill` 失败，再只改 description，比较 with/without plugin Δ。
2. **Codex AGENTS override debugging lab**：构造 global / repo root / nested 三层 `AGENTS.override.md` 与 `AGENTS.md`，让学员判断哪条指令生效，并观察 32KiB cap 的截断风险。
3. **Policy-as-skill lab**：把一个客户审批政策改写成 SKILL.md，强制包含 policy ID、scope、禁止外部动作、JSON schema、coordinator/specialist 写权限边界。
4. **Sandbox provisioning decision lab**：同一个 document-review POC 画 application-managed 与 webhook-managed 两版架构图，列出 cleanup / key isolation / provider handler 风险。
5. **Copilot adoption dashboard lab**：把 seat、chat、VS Code Agent window、code review、credits 五类指标拆成不同层，避免把“活跃 seat”误读为“agent 已落地”。
6. **MCP tool risk classifier lab**：给 10 个 Azure MCP tool 名称，让学员标记 read-only / state inspection / mutating / unknown，并写出 RBAC、审批、审计和回滚要求。

---

## 6. 原快照中 fail-loud / 未验证项

- 未安装或运行 Claude Code `plugin eval`，因此本文只给“设计门禁”，不承诺 CLI 行为在本环境可用。
- 未运行 OpenAI Cookbook Agents API 示例；Python 3.14、`uv`、sandbox provider、executor key 行为均未实测。
- Codex changelog 正文通过 JS 渲染页面/抓取取得；`https://learn.chatgpt.com/docs/changelog.md` 原快照中 404，不应把 `.md` 作为可复现源。
- Azure MCP beta.43 未安装包/未读全部 tool schema；对 IoT/Backup tool 的安全分类基于 changelog 摘要，生产前需 schema/RBAC/租户 smoke。
- Copilot metrics/code review changelog 未做企业租户 API dry-run；credits、策略可见性与分支保护交互仍需客户环境验证。
- `anthropics/commerce-agents` 为旧源复用；未运行或审计其完整实现。
