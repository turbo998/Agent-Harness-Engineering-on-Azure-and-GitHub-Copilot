<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 扩展控制面 + 运行证据日志 Checklist（2026-08-28）

> 用途：给 SA 在客户问“Copilot/Codex/Claude/本地 Agent 能不能接插件、MCP、企业策略、长任务恢复？”时快速落到 POC 验收与架构图。
> 安全红线：本文所有命令形态/配置键只作为上游证据与设计检查项，不是执行指令；POC 仅用 disposable fixture / 测试租户 / 测试 repo，不接客户生产代码、真实 secret 或生产 Azure 订阅。

## Evidence links（原研究快照中已确认可达）

| 来源 | URL | 证据强度 | 本资产采用的事实 |
|---|---|---|---|
| GitHub Copilot Customize tab GA | https://github.blog/changelog/2026-08-25-github-copilot-app-customize-tab-is-generally-available/ | docs body 200 | Customize tab 把 MCP servers / plugins / skills / canvases 聚合到 Copilot app；含 Azure DevOps backlog delegation 场景。 |
| GitHub Copilot managed settings autoUpdate | https://github.blog/changelog/2026-08-26-enterprise-managed-settings-now-support-autoupdate-for-plugin-marketplaces/ | docs body 200 | `extraKnownMarketplaces` 可对单个 plugin marketplace 设 `autoUpdate: true`；仍需 `strictKnownMarketplaces` allowlist 允许。 |
| GitHub Copilot Global model policy GA | https://github.blog/changelog/2026-08-26-global-model-policy-generally-available/ | docs body 200 | 未显式配置/新 GA 模型可委派给全局默认策略；显式 enable/disable 保留；open-weight 与不受数据保留协议覆盖模型默认不启用。 |
| Azure MCP Server beta.38 | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.38 | release page 200 + body snippets matched; no package/schema smoke | `search index query` 支持 full Lucene syntax；resilience tools 有多项改进；release body 仍含 `[Tool Count]` 占位，工具数不可引用。 |
| Microsoft Agent Framework Python 1.15.0 | https://github.com/microsoft/agent-framework/releases/tag/python-1.15.0 | release page 200 | A2UI、MiddlewareFailure、workflow checkpoint type registry、Foundry hosted steering/retry/recovery、OTel breaking。旧源复用；原研究快照中仅复用。 |
| Microsoft Agent Framework .NET 1.19.0 | https://github.com/microsoft/agent-framework/releases/tag/dotnet-1.19.0 | release page 200 | Azure Blob session persistence、Foundry hosted state persistence、agent-hooks experimental、MCP Tasks 2026-07-28 migration。旧源复用；原研究快照中仅复用。 |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | docs body 200 | 2.1.247 新增 `SendFeedback`、`/claude-api cost-optimize`、subagent model-404 fallback；2.1.246/243 作为上下文复用。 |
| ChatGPT/Codex changelog | https://learn.chatgpt.com/docs/changelog | docs body 200 + key snippets matched | 08-25 WebMCP site tools、event-triggered scheduled tasks；08-24 `codex mcp-server` deprecated→Codex app server；08-11 import from Claude/Cursor。 |
| OpenAI Cookbook Codex workflow | https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex | cookbook page 200 + body snippets matched | `AGENTS.md`、`GOALS.md`、`PLANS.md`、`PROMPTS.md`、`harness/build-log.md` 等为 workflow convention；本资产仅复用其规划/证据记录模式，不声称 Codex 必需这些文件。 |
| OpenAI Codex release 0.150.1 | https://github.com/openai/codex/releases/tag/rust-v0.150.1 | release page 200 | 0.150.1 仅确认 remote compaction retained images token-budget bugfix；不写成大功能。 |
| Apache Maka | https://github.com/apache/maka | README/page 200; no source audit | 本地优先 agent workspace；append-only runtime event log；Runtime Host；sandbox approval；eval cells/attempts/results。08-25 已雷达，原研究快照中首次深挖。 |

## 一张架构图的分层口径

```text
Entry / Collaboration
  Teams / Slack / Copilot app / ChatGPT desktop / Claude Code / Local desktop
        ↓
Capability Catalog / Marketplace
  MCP servers + plugins + skills + canvases + site tools(WebMCP)
        ↓
Policy Plane
  model policy + marketplace allowlist + autoUpdate + permission mode + approval rules
        ↓
Runtime Boundary
  cloud sandbox / local sandbox / Runtime Host / MCP server / Foundry hosted agent
        ↓
State + Evidence
  session persistence + checkpoint + append-only event log + build-log + telemetry/cost
        ↓
Review + Recovery
  HITL approvals + PR approval + hook/feedback + retry/recovery + audit export
```

## POC 验收清单（最小但可复用）

### 1. 能力入口与目录
- [ ] 列出用户入口：Teams、Slack、Copilot app Customize、ChatGPT desktop/Codex、Claude Code、本地 Maka-style desktop/CLI。
- [ ] 每个入口标明身份主体：用户身份、agent/session id、服务身份、连接器权限边界。
- [ ] 能力目录至少分四类：MCP server、plugin、skill、canvas/site tool；不要把它们混称为“插件”。
- [ ] 对 Copilot Customize tab 场景，画出“发现/安装能力”与“运行能力”的分离：目录发现≠已授权执行。

### 2. 企业策略面
- [ ] 模型策略：区分 `Enabled`、`Disabled`、继承组织/团队/app、`Delegate to default policy`；默认策略不是对所有模型无条件放行。
- [ ] 开源/open-weight 或不受数据保留协议覆盖模型：默认不启用；客户材料需单独确认租户策略与区域。
- [ ] 插件市场：`autoUpdate: true` 只是更新机制；仍必须被 `strictKnownMarketplaces` 允许，并要有版本回滚路径。
- [ ] 编码 Agent CLI：把 Claude Code Auto mode、Codex permission modes、Mistral/Grok hooks 视为“运行时授权层”，不要只画 prompt/skill 层。

### 3. Runtime 与状态恢复
- [ ] Microsoft Agent Framework：若采用 .NET/Python 新版本，POC 必测 session persistence / checkpoint / retry / recovery，不只测 happy path。
- [ ] Azure MCP Server：beta.38 的 Lucene search 与 resilience 工具需做 schema/help 级核实；release body 的 `[Tool Count]` 占位不可引用为真实工具数。
- [ ] Apache Maka 类本地 runtime：把 runtime.sqlite / append-only log / tool-call results / permission decisions 作为“证据层”，用于解释为什么短上下文不等于丢历史。
- [ ] Codex 0.150.1：原研究快照中只确认 compaction bugfix；POC 不应把 0.150.1 描述为新 harness 能力发布。

### 4. 证据与审计
- [ ] 每次工具调用记录：输入摘要、批准人/策略、结果、错误 envelope、耗时、token/cost 或估算。
- [ ] 每个长任务阶段记录：source inputs、acceptance criteria、verification command、observed result、skipped checks。
- [ ] 每个共享协作入口记录：谁发起、谁补上下文、谁批准 PR/高风险动作、conversation/thread link 的保留策略。
- [ ] 对 Claude Code 2.1.247：把 `SendFeedback` 和 subagent model fallback 视作“可恢复性/可诊断性”能力；客户演示前仍需临时 repo smoke。

## SA 快速回答模板

**客户问：我们要给企业部署 Agent 插件/技能生态，重点风险是什么？**

> 不建议只讨论“能不能装插件”。完整方案要分五层：入口、能力目录、策略面、运行边界、证据日志。GitHub Copilot 现在把 MCP servers / plugins / skills / canvases 汇到 Customize tab，企业又有全局模型策略和 marketplace autoUpdate；这意味着生产 POC 要验证 allowlist、版本更新、模型默认策略、审批、人审 PR 与审计日志。对于 Azure MCP/MAF，要额外测 session/checkpoint/recovery 与 MCP 工具错误 envelope。若是本地优先方案，可借鉴 Apache Maka 的 append-only runtime log，把短上下文优化与可审计历史分开。

## [→harness] 可直接反哺 workshop 的练习题

1. **Marketplace policy fixture**：创建假的 `managed-settings.json`，测试 marketplace allowlist + autoUpdate + rollback 表达；不连接真实 marketplace。
2. **Event-log fixture**：用本地 JSONL/SQLite 记录 5 次工具调用、2 次审批、1 次失败恢复，要求 reviewer 从日志复原结论。
3. **MCP output/failure contract**：模拟 Azure MCP search Lucene 查询、RBAC denied、timeout、large output truncation；验证错误 envelope 与 continuation token。
4. **Codex/Claude compatibility gate**：同一 repo 放 `AGENTS.md` + `CLAUDE.md` bridge + `harness/build-log.md`，检查模型策略、subagent fallback、feedback/report、context compaction 是否都有证据。

## Fail-loud gaps

- 未做任何真实租户、真实订阅、真实 CLI smoke；本文是资料级/设计级资产。
- 上游 release 中出现的 “production-ready sample” 仅代表样例发布口径；本资产未做包级 smoke、负载、安全或租户验证，不能据此承诺生产可用。
- GitHub API 匿名请求原研究快照中 403，star 数与部分 release body 以页面快照为准；不应作为客户报价或 SLA 依据。
- Apache Maka 尚未做源码安全审计；README 明确处于 Apache Incubating / early public release，不能作为生产推荐组件，只作架构模式参考。
- Codex scheduled tasks 08-25 的具体 GitHub blog slug 原研究快照中一个猜测 URL 返回 404；采用可达的 Codex changelog 页面为证据，不引用该错误 slug。
