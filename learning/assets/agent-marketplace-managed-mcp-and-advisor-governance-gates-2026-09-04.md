<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Marketplace / Managed MCP / Advisor Governance Gates — 2026-09-04

> 用途：给 SA 在客户问「如何把 Codex/Claude/Copilot/Foundry/Azure MCP 这些 agent 能力安全引入企业」时的可复用速查。本文是研究资产，不是执行 runbook；所有命令形态均为上游接口/工具名证据片段，**不要直接在客户或生产环境执行**。

## Evidence links（可复核来源）

| 证据层级 | 来源 | URL / 状态 | 原研究快照中命中要点 | Caveat |
|---|---|---|---|---|
| Release page + API snapshot | MAF Python 1.17.0 | https://github.com/microsoft/agent-framework/releases/tag/python-1.17.0 / page 200；release body 原快照中曾通过 GitHub API 抽取，匿名 API 可能受 rate limit 影响 | Foundry-hosted Telegram sample、history source 选择、OAuth consent recovery、approval stable occurrences、MCP init error surface | 未安装包/未运行样例 |
| Commit diff | Azure MCP Advisor update | https://github.com/microsoft/mcp/commit/cafb86ebb180b23acf52fb97717409fb9ec01650.diff / 200 | `advisor recommendation update`；New/Postponed/Dismissed/Completed；Security category state changes rejected；destructive/idempotent metadata | commit-level，未确认进入正式包 |
| Commit diff | Azure MCP Advisor metadata filters | https://github.com/microsoft/mcp/commit/bc2a3b4eeceb2281cdf944920b7fdb2ccc73f5df.diff / 200 | `--recommendation-type-id`、`--sub-category`、`--tracking-ids`、`--retirement-date`、`--status`；ARM-style result | commit-level，未确认进入正式包 |
| Product changelog | Copilot Code Review approval | https://github.blog/changelog/2026-09-01-copilot-code-review-can-now-approve-pull-requests/ / 200 | Copilot code review 可给 approval assessment | 租户策略/required approvals 真实配置未实测 |
| Product changelog | Copilot content exclusions GA | https://github.blog/changelog/2026-09-02-content-exclusions-generally-available-in-copilot-app-and-cli/ / 200 | Copilot app/CLI respect enterprise/org/repo content exclusions；agentic workflows 不使用 excluded files as context | 未在企业组织实测 |
| Product changelog | Copilot managed default model | https://github.blog/changelog/2026-09-02-enterprise-managed-settings-support-any-default-model/ / 200 | default model 可按 enterprise team 覆盖 | 「默认」不是「强制」；强制需另核策略 |
| Release page + API snapshot + docs markdown | Codex 0.153.0 | https://github.com/openai/codex/releases/tag/rust-v0.153.0 / page 200；release body 原快照中曾通过 GitHub API 抽取，匿名 API 可能受 rate limit 影响；https://learn.chatgpt.com/docs/build-skills.md / 200；https://learn.chatgpt.com/docs/build-plugins.md / 200 | release body 命中 remote marketplace list/install/remove、`tui.auto_recap=false`、experimental context management + `new_context`；build-skills.md 命中 progressive disclosure 与 `allow_implicit_invocation:false`；build-plugins.md 命中 universal plugin directory | 未 CLI smoke；context management 为 disabled-by-default/eligible sessions |
| Release page + API snapshot + docs | Claude Code 2.1.259 | https://github.com/anthropics/claude-code/releases/tag/v2.1.259 / page 200；release body 原快照中曾通过 GitHub API 抽取，匿名 API 可能受 rate limit 影响；https://code.claude.com/docs/en/plugin-marketplaces / 200 | `managedMcpServers`、headless `--permission-prompts none` 自动拒绝、`claude plugin validate --json`、marketplace.json/pluginRoot/skills/agents/hooks/MCP | 未 CLI smoke；docs 页面为HTML渲染但可达 |
| Official engineering blog | Anthropic containment | https://www.anthropic.com/engineering/how-we-contain-claude / 200 | sandbox/VM/egress controls、tool output、memory poisoning / persistent-context 风险、多 agent trust escalation | 工程博客级原则，不等于客户环境合规承诺 |
| Repo/raw README | Anthropic SCONE-Bench | https://github.com/anthropics/scone-bench / 200；https://raw.githubusercontent.com/anthropics/scone-bench/main/README.md / 200 | 417 smart-contract vulnerability tasks、MCP/stdio runner、docker/anvil local fork、grader restart 防作弊 | 未运行 benchmark，不引用性能数字 |

---

## 1. 企业 agent 控制面：三层分清，别混在一起讲

### Layer A — 配置/策略面（Enterprise policy）
- **Copilot content exclusions GA**：企业/组织/仓库级敏感路径排除进入 Copilot app/CLI；客户问「agent 会不会读敏感代码」时，第一句应从 content exclusion policy + 例外路径治理开始，而不是只说 prompt。
- **Copilot default model managed settings**：适合 FinOps/质量默认档；但它是默认值，不是硬性安全边界。若客户要强制模型、禁用某类模型、数据保留边界，需要另查 managed settings / allowlist / enterprise policy。
- **Claude `managedMcpServers`**：组织统一注入 HTTP/SSE MCP server；release notes 还显示 command-shaped entries 会被跳过，但生产前仍需以当前企业设置实测为准。这更像企业 MCP 目录/连接器控制面，不是每个开发者本地随便配 `.mcp.json`。

**SA 落点**：技术问答时先问「谁能配置？在哪里配置？是否可按团队覆盖？是否能审计？」；POC 时用测试组织验证策略下发与被拒绝路径；架构图上单独画 `Enterprise Policy Plane`，不要把它画成 agent runtime 内部模块。

### Layer B — 分发/扩展面（Marketplace / plugin / skill）
- **Codex 0.153.0**：plugin CLI 可从 remote marketplaces list/install/remove；OpenAI docs 显示 skills 采用 progressive disclosure，`agents/openai.yaml` 可声明 metadata、dependencies、`allow_implicit_invocation:false`。
- **Claude plugin marketplaces**：`marketplace.json` 可分发 skills、agents、hooks、MCP/LSP，并支持 `pluginRoot`、version pinning、跨 marketplace 依赖 allowlist。
- **风险**：plugin/skill 不是「Markdown 文档包」，而是可能包含 hooks、MCP、脚本、外部连接器的供应链入口。

**POC gate**：
1. 先做 local/private marketplace，不接公网未知 marketplace。
2. 每个 plugin 记录来源 URL、commit/tag、hash、许可证、hooks/MCP/commands/scripts 清单。
3. 默认 skills-only；有副作用或云控制面操作的 skill/plugin 设置显式调用或 `allow_implicit_invocation:false` / `disable-model-invocation:true` 等价策略。
4. 安装/更新/卸载必须有机器可读 validate 输出：Claude 可用 `plugin validate --json` 作为候选；Codex 需继续验证等价 lint/manifest 检查能力。

### Layer C — Runtime / tool execution plane
- **MAF 1.17.0**：approval 绑定 stable function-call occurrence、OAuth consent recovery、MCP init error surface、Foundry-hosted history source 选择，说明 runtime 正在补「恢复后不串审批/不重复回放/错误可见」这些工程细节。
- **Azure MCP Advisor update/filter**：Azure MCP 从 read-only 查询继续走向治理动作。Advisor update 是 destructive/idempotent metadata 的典型矛盾：业务上是“改状态”，技术上可幂等，但仍需要 RBAC、审批、rollback/audit。
- **Anthropic containment blog**：强调环境层边界（sandbox/VM/egress）优先于只靠模型监督；tool output、persistent memory、multi-agent trust escalation 是长期运行 agent 的关键风险面。

**架构图建议组件**：
`Agent Orchestrator` → `Policy Plane` → `Marketplace/Skill Catalog` → `MCP Gateway` → `Approval & Occurrence Ledger` → `Tool Runtime Sandbox` → `Audit/Evidence Store`。

---

## 2. 针对客户问答的速答模板

### Q1：Copilot / Codex / Claude 的 agent 能否读取被排除的代码？
**推荐答法**：
- Copilot app/CLI 官方 changelog 已宣布 content exclusions GA，并描述 agentic workflows 不使用被排除文件作为上下文；这是 Copilot 侧的策略能力。
- Codex/Claude 项目指令与 skills 仍需仓库级配置与验证；不要把 Copilot policy 自动推断为其它 CLI 的保护。
- POC 必须用 fixture 文件验证：被排除路径能否被搜索/读取/传给 subagent/tool output。

### Q2：能否让 Copilot code review 的 approval 算入 required approvals？
**推荐答法**：
- GitHub changelog 表明 Copilot code review 可给出 approval assessment；具体是否纳入 required-approval 门槛 取决于管理员/企业策略配置。
- 对生产合规仓库，建议只作为“辅助信号”先跑 2-4 周，与 CODEOWNERS、人类审批、CI/SARIF 做交叉验证，再决定是否纳入必需审批。

### Q3：Azure MCP 可以让 agent 自动处理 Azure Advisor 建议吗？
**推荐答法**：
- 最新 commit diff 已出现 Advisor recommendation update 与 metadata filters；但这是 commit-level 证据，尚未做包级/租户级 smoke。
- 对客户 POC：第一阶段只 list/filter；第二阶段对非 Security 类建议做 mock update；第三阶段才在测试订阅中验证 Completed/Dismissed/Postponed，必须绑定审批、RBAC、audit、rollback。

### Q4：要不要把内部 agent 能力做成 plugin marketplace？
**推荐答法**：
- 可以，但要按“企业私有目录 + 版本锁定 + 验证报告 + 权限最小化”做，而不是让团队自由安装社区 plugin。
- Codex 与 Claude 都在向 marketplace + skills + MCP 聚合；这有利于复用，但也把供应链风险集中到了 manifest/hooks/MCP server 上。

---

## 3. POC 最小验收清单（可复制）

| 验收项 | 最小 fixture | 通过标准 | 失败时说明 |
|---|---|---|---|
| Content exclusion | `public/ok.txt` + `secret/deny.txt` | agent 回答不引用 deny 内容；tool/search 结果不泄露 deny 路径 | 记录为 policy gap，不允许进入客户数据 |
| Plugin/skill install | 私有 marketplace + 1 个 instruction-only skill | 安装前后 manifest diff、validate JSON、卸载可回滚 | 若需执行 hook/MCP，升为安全审计 |
| MCP server 注入 | Claude managedMcpServers 或等价企业配置 | 只允许 HTTP/SSE 内部 server；command entry 被拒/跳过 | 本地命令式 MCP 不适合作为企业默认注入 |
| Advisor read/list | fake/test subscription 或 mock ARM | list/filter/status/metadata 输出可解释，错误 envelope 稳定 | 不可解释错误不能给客户演示 |
| Advisor update | mock 或测试订阅非生产建议 | destructive/idempotent 标记明确；Security 类拒绝；审批+audit 记录完整 | 不满足拒绝/审批即禁止自动化治理 |
| Approval recovery | synthetic function call + interruption/replay | occurrence id、provider call_id、approval result 不错配 | 这是 runtime blocker |
| Context management | 长对话 + recap/new_context 开关 | 自动/手动 recap 不丢决策；experimental 功能标明范围 | disabled-by-default 不得承诺客户可用 |
| Eval/security bench | SCONE-Bench 式 local fork 思路或 toy task | runner、grader、reset、防作弊、artifact 均可复核 | 不引用 benchmark 性能数字 |

---

## 4. [→harness] 可直接反哺 workshop 的练习卡

1. **Marketplace lifecycle lab**：用私有/local marketplace 安装一个 instruction-only plugin/skill，做 install → validate → invoke → uninstall → evidence log。
2. **Content exclusion lab**：在临时 repo 放置允许/禁止两组文件，让 Copilot/Codex/Claude 分别尝试读取，记录每栈的真实边界；不要拿某一栈结论泛化到所有栈。
3. **Advisor governance lab**：用 mock Azure Advisor payload 实现 list/filter/update 三段式；update 必须过 approval ledger，Security 类建议 fail-closed。
4. **Occurrence replay lab**：模拟 function-call approval 中断与恢复，检查 stable occurrence id 与结果绑定。
5. **SCONE-style eval lab**：借鉴 SCONE-Bench 的“local fork + runner + grader reset”思想，用非区块链 toy domain 做防作弊 evaluator，不运行真实资金或主网交互。
6. **Containment threat model lab**：把 sandbox/VM/egress/tool-output/memory-poisoning/subagent-trust 六项画成威胁模型，作为任何 agent POC 的 preflight。

---

## 5. 什么时候不要做

- 客户没有测试租户/测试仓库/假数据：不要接 MCP/Advisor update/插件 marketplace。
- 客户只问“能不能用”：不要直接给“能”，应拆成 product availability、tenant policy、runtime verification、compliance boundary 四层。
- 证据只有 commit diff：不要承诺已进入正式包；写“commit-level signal，待 release/package smoke”。
- 页面/博客可达但未读正文：只能作为 radar，不写强结论。

## 6. 本资产的使用边界

- 适合：客户技术问答、POC preflight、架构图组件、harness workshop 练习设计。
- 不适合：作为生产变更 runbook、合规承诺、价格/配额/区域可用性证明。
- 任何 Azure/GitHub/M365 租户级策略必须在目标租户二次核实；本文只记录 2026-09-04 原快照中可达证据。
