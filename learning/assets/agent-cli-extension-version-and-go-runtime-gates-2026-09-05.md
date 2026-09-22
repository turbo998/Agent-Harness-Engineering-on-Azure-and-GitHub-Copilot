<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent CLI Extension / Version Watch / Go Runtime Gates（release/docs-derived pre-smoke, 2026-09-05）

> 用途：把 2026-09-05 快照核实到的 Microsoft Agent Framework Go、Azure MCP beta.41、Codex/Claude Code、Mistral Vibe、Google agents-cli 的更新，压缩成 SA 可复用的技术问答/POC/架构图检查清单。
> 安全说明：本文中的命令形态（如 `azmcp ...`、`/mcp login`、`agents-cli deploy`）均为上游 release/changelog 中的工具名或功能名证据，不是执行指令。任何 POC 都必须在临时 fixture / 测试订阅 / 无真实 secret 环境中验证。

## Evidence links（原快照中已验证可达）

| Source | URL | Evidence tier | Caveat |
|---|---|---|---|
| Azure MCP Server 3.0.0-beta.41 release | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.41 | release HTML 200；正文命中 tool count 485、IoT/resilience | 未安装包、未连 Azure 订阅；工具数仅 release 自述 |
| Azure MCP raw CHANGELOG | https://raw.githubusercontent.com/microsoft/mcp/main/servers/Azure.Mcp.Server/CHANGELOG.md | raw 200；逐段读取 beta.41 | 只读 changelog，未验证 tool schema |
| Microsoft Agent Framework Go v0.1.0 | https://github.com/microsoft/agent-framework-go/releases/tag/v0.1.0 | release HTML 200；Public Preview release notes | Preview，API 可能变化；未运行 Go SDK |
| OpenAI Codex 0.153.3 | https://github.com/openai/codex/releases/tag/rust-v0.153.3 | release HTML 200；npm latest 200 | 未运行 CLI；0.154 alpha 仅版本信号 |
| OpenAI Codex changelog | https://developers.openai.com/codex/changelog → https://learn.chatgpt.com/docs/changelog | redirect后200；正文 grep 命中 `/import`、hooks、MCP | JS/docs 页面需记录 resolved URL；功能可用性未实机 |
| OpenAI Codex what’s-new | https://developers.openai.com/codex/whats-new → https://learn.chatgpt.com/docs/whats-new | redirect后200；正文 grep 命中 Aug31-Sep4、attachments、import | 周报/产品层 evidence，不倒灌成 CLI release 功能 |
| Claude Code changelog | https://code.claude.com/docs/en/changelog and https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | docs/raw 200；raw 命中 2.1.260 | 未运行 Claude Code |
| Claude Code skills docs | https://code.claude.com/docs/en/skills | docs 200；命中 `allowed-tools`、`when_to_use`、`disable-model-invocation` | 已是近期旧源复用+字段补强，不当全新发现 |
| Mistral Vibe v2.25.0 | https://github.com/mistralai/mistral-vibe/releases/tag/v2.25.0 | release HTML 200；正文含 `/skills`、MCP login、ACP connectors | Experimental off by default；未审源码/插件权限 |
| Google agents-cli v1.5.0 | https://github.com/google/agents-cli/releases/tag/v1.5.0 | release HTML 200；extension system + LangChain template | 未运行 Google Agent Runtime；扩展安装面需供应链审计 |
| Community Codex plugin radar | https://github.com/hashgraph-online/awesome-codex-plugins | repo 200；URL-only / README-snippet radar；旧源复用 | 旧源复用，非新发现；不推荐直接安装，需逐插件审 manifest/hooks/MCP/network |
| Community Claude/subagent/lint radar bundle | https://github.com/hesreallyhim/awesome-claude-code ; https://github.com/VoltAgent/awesome-claude-code-subagents ; https://github.com/giacomo/agents-lint | repo URLs 200；仅资料池 | 未审 hooks/MCP/network/license/autofix；不安装、不推荐，只作后续候选入口 |

## 一句话结论

本周最值得吸收的不是某个单点功能，而是 **Agent 工具体系正在把“扩展/skills/plugins/MCP/connector/approval/eval”做成跨运行时控制面**：微软 Go SDK 补齐语言面，Azure MCP beta.41 把云控制面工具继续扩展到 Advisor/Resilience，Codex/Claude/Mistral/Google CLI 都在强化 extension/import/skill/headless/eval 能力。SA 的交付物应从“能不能跑”升级为“扩展入口是否可治理、版本漂移是否可追踪、工具输出是否可回放”。

## 技术问答速答模板

### Q1：客户问“能不能用 Go 写 Microsoft Agent Framework agent？”

**回答**：可以进入评估，但要明确这是 v0.1.0 Public Preview，不是 GA 承诺。release notes 明确支持 streaming、structured output、sessions/history、tool calling、middleware、approvals、graph workflows、checkpointing、HITL、多 agent 协作、Foundry/OpenAI/Anthropic/Gemini/GitHub Copilot/MCP/A2A/AG-UI 集成以及 OpenTelemetry tracing。

**建议口径**：
- POC 可以用 Go SDK 做非生产评估，重点验证 tool calling、approval、checkpoint、OTel trace 与 A2A/MCP 互通。
- 生产落地仍建议按客户语言栈、preview 风险、SDK maturity 选择：.NET/Python 更稳，Go 适合 Go-first 团队抢先验证。
- 若涉及 acted-for user identity / approval context，09-04 post-release commits 只作为线索；进入客户材料前必须读 diff + 包级 smoke。

### Q2：Azure MCP beta.41 能不能直接让 agent 更新 Advisor recommendation / resilience drill？

**回答**：只建议在测试订阅做 gated POC，不建议直接给生产 agent 开写权限。beta.41 changelog 显示 Advisor list 变为 ARM-style payload，支持 status / tracking IDs / retirement / recommendation type 等 metadata filters，并新增 Advisor update 以及 resilience drill add-or-update / validate / mark-complete 等工具。

**POC gate**：
1. Schema gate：确认调用方从旧 flat 字段迁移到 `id/name/type/properties`，特别是 impacted resource ID 和 short description 的新路径。
2. RBAC gate：测试 New/Postponed/Dismissed/Completed 的权限差异；Security 类别历史上有额外限制，beta.41 changelog 表示 now returns no matching recommendations for incompatible combinations，不等于所有 update 都可写。
3. Approval gate：凡是 update / mark-complete / add-or-update 都加 HITL、reason、ticket、rollback note。
4. Audit gate：记录 subscription、resourceId、recommendation id、old state、new state、actor、agent run id、tool args、HTTP status。

### Q3：Codex/Claude Code 本周对 harness 最大影响是什么？

**回答**：Codex 侧是 version/source watcher 与迁移入口：npm latest 已到 0.153.3，release 增加 Bedrock model picker/async-question guidance；官方 changelog/what’s-new 继续强调 `/import`、attachments、hooks、subagents、MCP tool hooks、`/init` 与 auto-review。Claude Code 侧是 2.1.260 的 headless/observability：`/diff`、prompt-cache miss likely cause、headless `/reload-plugins`、`/advisor` 与多项 sandbox/permission/path 修复。

**Harness 回归项 [→harness]**：
- Version matrix：`codex_npm_latest`、`codex_release_tag`、`codex_docs_last_modified`、`claude_raw_changelog_version` 分开记录，避免 docs lag。
- Import dry-run：在临时 repo 对 Codex `/import` 导入 Claude/Cursor setup 的生成物做 diff，不触碰客户仓库。
- Hook order：Interrupt/Stop/MCP tool hooks 的 occurrence id、error envelope、replay 行为要有 EVIDENCE log。
- Cache observability：Claude `/cost` / status line 的 prompt-cache miss cause 进 nightly telemetry，而不是只看 token 总量。

### Q4：Mistral Vibe / Google agents-cli 能给微软合作伙伴什么启发？

**回答**：它们不是微软栈替代品，但提供了跨厂商 extension control-plane 的对照样本。

- Mistral Vibe v2.25.0：`/skills` browser、shared skills sync、plugin-declared MCP servers、`/mcp login`、ACP connectors、session model pinning、prompt queue controls。**启发**：插件 MCP server 必须按 session/插件身份隔离，同名 server 不能共享凭据；skills sync 要有版本 pin 与缓存清理策略。
- Google agents-cli v1.5.0：extension system + LangChain template、从 GitHub/本地路径安装扩展、`infra show`、deploy update-only、labels、eval QPS。**启发**：Agent Runtime POC 不只要部署，还要有 infra introspection、idempotent update、标签治理和 eval rate control。

## POC 验收清单（可复制）

> 执行安全红线：以下清单先用于 mock/dry-run/临时 fixture，不复制到生产订阅、客户仓库或真实 MCP/connector 凭据环境直接执行。

### A. Version and evidence gate

- [ ] 每个 agent CLI/SDK 记录：package latest、release tag、docs/changelog URL、raw changelog URL（如有）、采集时间。
- [ ] 如果 release body 是空壳/模板，只记版本信号，不写功能断言。
- [ ] 如果 docs URL redirect，记录 resolved canonical URL。
- [ ] 星标/下载量只作雷达，不作为客户推荐依据，除非原快照中独立核实。

### B. Extension / plugin / skill intake gate

- [ ] Manifest：名称、版本、来源、许可证、安装范围、默认启用状态。
- [ ] Executable surfaces：hooks、commands、statusline、MCP server、post-install、auto-update。
- [ ] Credential boundary：是否读取 user config、env、keychain、MCP token；同名 server 是否可能共享凭据。
- [ ] Network boundary：默认外联目的地、proxy、split-horizon rewrite、telemetry。
- [ ] Rollback：禁用、卸载、清理缓存、撤销 MCP login / connector token。
- [ ] Evidence：所有变更写入 `EVIDENCE/plugin-intake.md`，包括不通过原因。

### C. Azure MCP Advisor/Resilience gate

- [ ] Read-only first：先跑 list/get/validate，不先跑 update/mark-complete/add-or-update。
- [ ] Output schema：验证 flat→ARM-style payload 迁移。
- [ ] Human approval：写操作必须有 approval record + reason + ticket。
- [ ] RBAC denial：模拟/测试 403、资源不存在、category/filter 不兼容、ARG >1000 paging。
- [ ] Rollback/runbook：Postponed/Dismissed/Completed 的业务含义由云治理 owner 确认。

### D. Runtime parity gate（MAF Go / Mistral / Google / Codex / Claude）

- [ ] Streaming：能否保留 event id / turn id / interrupt 状态。
- [ ] Structured output：能否 schema validate + 大输出截断/continuation。
- [ ] Approval：工具调用前后的 occurrence id 是否稳定。
- [ ] Checkpoint/resume：kill/restart 后 session / queued prompt / plugin MCP 状态是否恢复。
- [ ] Observability：OTel/App Insights/eval trace 是否含 model、tool、latency、cache hit/miss、approval。
- [ ] Isolation：每 session / repo / plugin / MCP server 是否隔离凭据与状态。

## 架构图组件（文字版，可转SVG）

```text
[Repo / Project]
  |-- AGENTS.md / CLAUDE.md / SKILL.md / plugin manifest
  |-- EVIDENCE/ version-matrix.json + plugin-intake.md
  v
[Agent CLI / SDK Control Plane]
  |-- Codex: /import, /init, hooks, subagents, auto-review
  |-- Claude Code: skills, headless commands, cache diagnostics
  |-- Mistral Vibe: /skills, /mcp login, ACP connectors
  |-- Google agents-cli: extensions, infra show, deploy update-only, eval qps
  |-- MAF Go: approvals, graph workflows, OTel, MCP/A2A/AG-UI
  v
[Tool / Extension Runtime]
  |-- MCP servers / connectors / cloud control-plane tools
  |-- HITL approval + RBAC + credential isolation
  |-- output schema + error envelope + continuation
  v
[Governance Evidence]
  |-- audit log / trace / eval scorecard / rollback notes
  |-- nightly version watcher / URL health / release-body gate
```

## 反哺 harness workshop 的练习卡 [→harness]

1. **版本漂移实验**：给一个临时 repo 写 `EVIDENCE/version-matrix.json`，分别记录 Codex npm latest、GitHub release、docs changelog、Claude raw changelog；要求学员解释“release tag 新但 body 空壳”时为什么不能写功能断言。
2. **Plugin intake lab**：用一个 toy plugin manifest（不含真实外联）标注 executable surfaces、MCP server、credential boundary、rollback；拒绝安装未知社区 plugin。
3. **Azure MCP Advisor dry-run**：用 mock JSON 模拟 beta.41 ARM-style payload，写 parser migration test，确保旧 flat 字段访问失败时 fail loud。
4. **Runtime parity smoke**：同一合成任务分别映射到 MAF Go / Codex / Claude / Mistral / Google 的“approval + resume + trace + output schema”四个检查点，输出一张 scorecard。

## Fail-loud / 未完成

- 未安装或运行任何 CLI/SDK/package；所有功能均停留在 release/docs/raw evidence 层。
- `microsoft/agent-framework-go` 09-04 user identity / approval context commits 仅 URL 200，未读 diff；不写入客户材料的功能承诺。
- `hashgraph-online/awesome-codex-plugins` 只作为社区 radar，不推荐安装，未审每个插件的 hooks/MCP/网络/许可证。
- Azure China / Global 可用性、M365/GitHub Enterprise 策略实际租户行为未验证；客户项目必须按目标租户另核。
