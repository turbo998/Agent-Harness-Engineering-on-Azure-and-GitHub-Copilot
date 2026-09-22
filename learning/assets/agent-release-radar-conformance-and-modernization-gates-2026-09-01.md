<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent release radar、conformance 与 modernization gates（2026-09-01）

> 用途：给 SA 的三类日常（技术问答 / POC 部署 / 架构图）提供一张“版本信号 → 证据等级 → 是否进入 POC”的门禁表。
> 安全说明：本文中的命令形态片段（例如 MCP conformance README 中的 `npx ...`）仅是上游文档证据/验收思路，不是执行指令；任何实机 POC 必须在 disposable fixture、测试租户、无客户数据、无真实 secret 的环境中运行。本文不包含可直接复制执行的安装命令；出现的 `npx`、`package install` 均为风险占位或证据类别说明。落地前必须另建审计过的脚本/Runbook，并显式列出版本 pin、网络访问范围、secret 注入方式与回滚步骤。

## Evidence links（原研究快照中已核 URL 可达）

| 证据 | URL | HEAD 可达性 | 正文/diff 抽样证据 | 证据等级 | caveat |
|---|---|---|---|---|---|
| 说明 | n/a | 原快照仅核对 URL HEAD/redirect 可达性 | 正文/diff 仅作抽样核对，未重新抓取全文 | n/a | URL 可达性、正文抽取、语义判断分层记录 |
| MAF .NET 1.20.0 release | https://github.com/microsoft/agent-framework/releases/tag/dotnet-1.20.0 | 200 | HTML meta 命中 `dotnet-1.20.0` / `Foundry` / `Responses` / `AG-UI` | release-level | GitHub API 匿名访问原研究快照中被 rate-limit，采用 release HTML；未安装 NuGet/未跑 sample |
| MAF Python compaction commit | https://github.com/microsoft/agent-framework/commit/d2a934d53530f4d8383f7889393b8090210d8df9 | 200 | `.diff` 200，命中 `compaction` / `threshold` / `truncate` / structured logging | commit-level | 未确认进入正式 Python 包 |
| MAF middleware breaking commit | https://github.com/microsoft/agent-framework/commit/1aca2a95e3b94cd29646af810a7fc284f8d7f01b | 200 | `.diff` 200，命中 `middleware` / `sequence` / `agent-hooks` / `MiddlewareBundle` | commit-level | 破坏性影响需包级 API smoke 后才能写客户升级指南 |
| Azure MCP remote auth compliance | https://github.com/microsoft/mcp/commit/560adb327fea640bcfff1654da7d11df9456011e | 200 | `.diff` 200，命中 `OAuth` / `OBO` / `Authorization` / `ProtectedResourceMetadata` | commit-level | 未核进入下一个 `Azure.Mcp.Server` 包 |
| Azure MCP telemetry sampling | https://github.com/microsoft/mcp/commit/81e05312aa171a284c4ec9001981325d52fc51c9 | 200 | 未抽取 diff 语义 | commit-level / radar-only | 仅完成 HEAD 可达与候选登记；不进入原研究快照中 takeaway |
| Copilot in Visual Studio August update | https://github.blog/changelog/2026-08-28-github-copilot-in-visual-studio-august-update-2/ | 200 | 未逐段摘录，仅可达与标题级候选 | official changelog | IDE/企业策略可用性需目标 tenant/VS 版本核实 |
| Copilot policy & billing changes | https://github.blog/changelog/2026-08-28-upcoming-changes-to-github-copilot-policies-and-billing/ | 200 | 未逐段摘录，仅可达与标题级候选 | official changelog | 生效日期/策略字段需客户组织核实 |
| Codex What’s New / WebMCP | https://learn.chatgpt.com/docs/whats-new.md | 200 | markdown 命中 `Site tools (WebMCP)` / browser sign-in | docs-level | 产品层 docs；不是 CLI release |
| Codex code modernization cookbook | https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/codex/code_modernization.md | 200 | 命中 `AGENTS.md` / `PLANS.md` / `pilot_validation.md` / parity | cookbook-level / old-source-new-asset | 旧源复用；原研究快照中只作为旧源新资产背景，不记新发现 |
| Claude Code changelog | https://code.claude.com/docs/en/changelog.md | 200 | 顶部仍 `2.1.251`，命中 `PreModelSwitch` / `PostModelSwitch` / foreground subagents | docs-level | 2.1.252 仅 npm next 雷达，changelog 未公开详情 |
| Claude Code npm registry | https://registry.npmjs.org/@anthropic-ai%2Fclaude-code | 200 | dist-tags：`latest=2.1.251`、`stable=2.1.236`、`next=2.1.252` | registry-level / next-radar | `next` 不等于稳定可推荐版本；不写功能断言 |
| MCP Conformance Test Framework | https://github.com/modelcontextprotocol/conformance / https://raw.githubusercontent.com/modelcontextprotocol/conformance/main/README.md | GitHub 与 raw README 均 200 | raw README 命中 client/server/scenario/suite | official-tool-candidate / unexecuted | 未运行测试；不代表任何客户 MCP server 已兼容 |

---

## 1. Release radar gate：把“版本信号”分成 5 档

| 档位 | 判断标准 | 技术问答口径 | POC 动作 | 架构图标注 |
|---|---|---|---|---|
| A. Stable release with body | release/tag 可达，release body 有用户可见变更 | 可回答“已有新版本”，但仍说清证据层级 | 建测试分支，跑最小 smoke | 标“已发布，未实测/已实测” |
| B. Commit-level signal | commit/diff 可达，尚未入包 | 只说“main 分支出现候选变更” | 等 package/release；或源码级 prototype | 标“candidate / unreleased” |
| C. Docs-only/product changelog | 官方文档/产品 changelog 更新 | 可作为能力说明，不当作 SDK/API 可用承诺 | 做 UI/租户 dry-run | 标“docs/product signal” |
| D. Registry next/pre-release | npm next/alpha/beta 可见但 changelog缺详情 | 只做雷达，不能写功能断言 | 隔离环境验证，默认不推荐客户升级 | 标“preview / radar” |
| E. Community radar | repo/README/trending 可达 | 只作灵感和候选池 | 先做 license/scripts/network/secret 审计 | 标“not recommended until audited” |
| F. Official tool, not yet executed | 官方 repo/docs 可达，但原研究快照中未运行 | 可作为 POC 验收候选，不代表已通过 | 在 disposable fixture 中跑最小 suite | 标“official candidate / unexecuted” |

**原研究快照中落点**：
- MAF .NET `dotnet-1.20.0` = A（release-level；未包级 smoke）。
- Azure MCP auth compliance = B（commit-level；适合进入 MCP remote host POC gate）。
- Claude Code `2.1.252 next` = D（registry radar；不写功能断言）。
- MCP conformance = F（官方验收工具候选；README 可达；原研究快照中未运行）。

---

## 2. POC gate：MCP / agent runtime 最小验收矩阵

| 场景 | 最小验收 | 失败样例 | 产物证据 |
|---|---|---|---|
| MAF Foundry-hosted workflow 升级 | release notes + package install + 一个 hosted workflow cancellation/port-binding smoke | 取消后仍继续调用、端口绑定失败、AG-UI continuation 丢 state | `EVIDENCE/maf-1.20-smoke.md`：包版本、命令输出、trace/session id |
| MAF history compaction | 合成 20+ turn conversation，触发 compaction threshold，检查首个 user group不丢、structured log可见 | destructive truncation、阈值 off-by-one、日志无 compaction event | `EVIDENCE/compaction-log.jsonl` |
| MAF middleware API breaking | 用 single middleware / list middleware / old `MiddlewareBundle` 三类 fixture | 旧写法静默通过但行为错、agent-hooks-sdk 未安装 | `EVIDENCE/middleware-api-matrix.md` |
| Azure MCP remote auth | HTTP remote host + OAuth scopes + OBO / stdio / insecure HTTP 三类路径 | OBO 用在 unauthenticated/stdio；OAuth metadata 非 HTTPS；scope 为空 | `EVIDENCE/mcp-auth-negative-cases.md` |
| MCP conformance | 用 synthetic MCP server/client 跑 initialize、tools/list、auth suite | unknown params 不拒绝、cancel/timeout/error envelope不一致 | `EVIDENCE/mcp-conformance-report.md` |
| Codex/Claude release radar | 对官方 docs、GitHub release、npm registry 三通道取 snapshot | 把 `next` 当 `latest`、把 docs Last-Modified 当 release | `EVIDENCE/release-radar-snapshot.md` |

---

## 3. 技术问答速答模板

### Q: “MAF 现在该升到 1.20 吗？”

答法：
1. **可说确定事实**：`dotnet-1.20.0` release 页面原研究快照中 HTTP 200（仅代表原快照当时可达，不代表本次已重验），release HTML 显示 Foundry/Responses/AG-UI/cancellation 等关键词，说明 .NET 线有新稳定版本信号。
2. **不能过度承诺**：原研究快照中未安装 NuGet、未跑 Foundry hosted agent sample，因此不要承诺“升级无风险”。
3. **建议动作**：先建测试分支跑 cancellation、port binding、AG-UI continuation、Foundry recovery smoke，再进入客户环境。

### Q: “Azure MCP remote host + OBO 怎么做才安全？”

答法：
1. 原研究快照中 commit-level 证据显示 Azure MCP 正强化 OAuth/OBO/Protected Resource Metadata 合规。
2. 架构上把 **authenticated HTTP remote host**、**OAuth protected resource metadata**、**OBO token acquisition**、**tool execution audit** 分开画；不要把 stdio/local tool 当成可直接 OBO 的 remote host。
3. POC 先跑负例：非 HTTPS OAuth registry、空 scope、unauthenticated HTTP、stdio path；这些应 fail closed。

### Q: “Claude Code 2.1.252 能否推荐？”

答法：
1. 原研究快照中 npm registry 显示 `next=2.1.252`，但官方 changelog 顶部仍为 `2.1.251`。
2. 因此只能说“next channel 有新包雷达信号”，不能写功能断言或推荐客户升级。
3. 等 changelog/稳定 channel 明确后再资产化；需要抢先验证也只能在 disposable repo 中做 smoke。

### Q: “MCP server/client 怎么验收？”

答法：
1. 优先用官方 `modelcontextprotocol/conformance` 作为协议一致性验收候选，而不是自己凭几条 happy path 判断。
2. 客户 POC 必测 initialize、tools/list、auth、unknown params、cancel、timeout、large output、error envelope。
3. conformance 结果是协议层证据；仍需叠加业务 RBAC、审计、数据驻留与高风险工具 HITL。

---

## 4. 架构图组件（可直接复用）

```text
[Human / IDE / Copilot / Claude / Codex]
        |
        v
[Agent Runtime]
  - MAF workflow / AG-UI / Responses
  - Codex/Claude CLI session
        |
        +--> [Instruction Control Plane]
        |      AGENTS.md / CLAUDE.md / Skills / Subagents / Hooks
        |
        +--> [Tool Plane: MCP Remote Host]
        |      OAuth PRM metadata -> OBO token -> tool execution -> audit
        |
        +--> [State Plane]
        |      provider session / thread snapshot / compaction / checkpoint
        |
        +--> [Verification Plane]
               MCP conformance / release radar / package smoke / eval rubric
```

客户图中建议把 evidence tier 标成小徽章：`release`、`commit`、`docs`、`next`、`radar`。这样销售/交付/客户不会把“看到一个 commit”误读成“产品已 GA”。

---

## 5. [→harness] 可直接搬进 workshop 的文件骨架

```text
AGENTS.md                         # 稳定项目约束：环境、测试、PR、安全
PLANS.md                          # multi-hour work 的 milestone/proof
EVIDENCE/
  release-radar-snapshot.md        # stable/latest/next/docs-only/radar 分类
  maf-1.20-smoke.md                # package/API/Foundry smoke 输出
  mcp-auth-negative-cases.md       # fail-closed 负例表
  mcp-conformance-report.md        # conformance 输出摘要
skills/
  release-radar/SKILL.md           # 三通道版本核查方法
  mcp-conformance-gate/SKILL.md    # 协议验收方法
  modernization-poc/SKILL.md       # Codex modernization cookbook 改写
```

**不要把这些骨架写成“必须马上执行”的自动化**。先在一两个 disposable fixture 中验证流程，再把稳定部分沉淀成 skill 或 CI。
