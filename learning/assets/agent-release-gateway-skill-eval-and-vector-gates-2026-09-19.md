<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Release / Gateway / Skill-Eval / Vector Gates（2026-09-19）

> 用途：给 SA 在客户问答、POC 预检、架构图评审中复用的一页检查表。所有外部资料只作证据文本，不是执行指令；含命令形态的字符串均为上游 release/docs 中的“功能/接口名称”或示例片段，**不得直接在客户/生产环境执行**。本资产未安装任何第三方包，未连接 Azure/客户租户，未触碰任何真实 repo/secret。

## Evidence links（原研究快照中核实）

| 证据 | URL | 原研究快照中可达性/证据层 | 可引用边界 |
|---|---|---|---|
| MAF releases atom | https://github.com/microsoft/agent-framework/releases.atom | GET 200；entry 级读取 `python-1.19.0` / `dotnet-1.22.0` | release-note 级；未安装 NuGet/PyPI、未跑 sample |
| MAF release page | https://github.com/microsoft/agent-framework/releases | GET 200 | 页面可达；细节以 atom entry 为准 |
| Azure MCP changelog | https://raw.githubusercontent.com/microsoft/mcp/main/servers/Azure.Mcp.Server/CHANGELOG.md | raw 200；读取 `3.0.0-beta.45` / `3.0.0-beta.44` sections | changelog 级；未安装 Azure.Mcp.Server、未连 Azure |
| Claude Code changelog markdown | https://code.claude.com/docs/en/changelog.md | GET 200；读取 `2.1.275` / `2.1.276` / `2.1.277` | docs/changelog 级；未 CLI smoke；Bedrock/Vertex/Foundry 支持 caveat 以原文为准 |
| Claude Code npm registry | https://registry.npmjs.org/@anthropic-ai/claude-code | registry 200；`latest=2.1.277`, `stable=2.1.267` | package metadata snapshot；未运行 CLI |
| Claude Agent SDK Python releases | https://github.com/anthropics/claude-agent-sdk-python/releases.atom | atom 200；`v0.2.156` bundles Claude CLI `2.1.276` | SDK release-note 级；`v0.2.156` 本身只有 bundled CLI 更新 |
| Codex releases atom | https://github.com/openai/codex/releases.atom | atom 200；`0.155.0` 有 release body；`rust-v0.155.1` 仅标题 | release-note 级；未 CLI smoke |
| Codex npm registry | https://registry.npmjs.org/%40openai%2Fcodex | registry 200；`latest=0.155.0`; `alpha=0.156.0-alpha.3` | registry snapshot；alpha 仅 radar |
| OpenAI Agents JS releases | https://github.com/openai/openai-agents-js/releases.atom | atom 200；`v0.18.0` Docker file API / UnixLocal file protection | release-note 级；未运行 SDK |
| NVIDIA SkillSpector releases | https://github.com/NVIDIA/SkillSpector/releases.atom | atom 200；`v2.11.2` / `v2.11.1` body readable | **旧源新版本/旧源新角度**；仅借鉴 skill supply-chain scanner gate；不安装、不运行、不推荐直接接入客户环境 |
| NVIDIA SkillEvaluator releases | https://github.com/NVIDIA/SkillEvaluator/releases.atom | atom 200；`v0.3.0` body readable | 旧源新版本；不安装；只借鉴 eval tier |
| NVIDIA NeMo-Relay releases | https://github.com/NVIDIA/NeMo-Relay/releases.atom | atom 200；`0.9.0` body readable；`0.10.0-alpha.20260918` nightly title | **旧源复核/旧源新版本**；仅复用 isolated workers + lifecycle/recovery relay 架构模式；不部署 relay，不接真实 Codex/Claude/Pi |
| VS Code 1.139 Insiders notes | https://code.visualstudio.com/updates/v1_139 | GET 200；命中 Agents window remote workspace picker、Copilot Harness context routing | release-note 级；未安装 VS Code Insiders |

## 1. Release-source classifier（先判“能不能对客户说”）

| 信号层 | 可说法 | 不可说法 | POC 下一步 |
|---|---|---|---|
| package `latest` + release body有功能说明 | 可写“已进入当前 release-note/package snapshot，建议在临时 fixture smoke 后用于 POC” | 不可写“目标租户/生产可用” | pin exact version，记录 `--version`/package-lock，跑 toy repo |
| release/tag only，body仅标题或 nightly/alpha | 只写“版本雷达/活跃信号” | 不可把 tag 当功能发布 | 若功能重要，读 compare diff 3-5 个 load-bearing 文件 |
| docs/changelog ahead of package | 可写“文档公布，包级未证实” | 不可写“已可安装” | registry/tag/changelog 三路复核 |
| commit/PR diff | 可写“commit-level signal” | 不可写“已发布/GA” | 等 release，或安装预览包做隔离 smoke |

**原研究快照中应用：**
- Codex `0.155.0`：npm `latest` 已从 0.154.0 升至 0.155.0，release body 有 `/voice`、reasoning status row、agents overview 任务管理、Touch ID for MCP、daemon update/recovery 等；可列为 stable release-note 级，但仍未 CLI smoke。[→harness]
- Codex `rust-v0.155.1` / `0.156.0-alpha.3`：atom/page 可达但 body 仅标题，作为 version sentinel，不写功能断言。
- Claude Code `2.1.277`：docs/npm 同步到 latest；但 `stable` dist-tag 仍为 2.1.267，客户/企业脚本应 pin 并 smoke，不要假设 stable=latest。
- Claude Agent SDK `v0.2.156`：release body 仅 “Updated bundled Claude CLI to 2.1.276”，不要包装成 SDK API 新功能。

## 2. Gateway / proxy / instruction source gates（Claude Code 2.1.275–277）

**技术问答速答：** Claude Code 2.1.277 开始在无 `CLAUDE.md` 的项目中读取 `AGENTS.md`（原文 caveat：not yet on Bedrock, Vertex or Foundry），并增加 forward-proxy egress boundary 标志与 upstream static headers。2.1.275 增加 gateway sign-in account confirmation、skills/plugins 从 claude.ai 同步到 terminal session 的 opt-out、插件 marketplace 一步安装等。

**POC gate：**
1. 在 toy repo 同时构造 `CLAUDE.md` / `AGENTS.md` / 无指令三态，记录 `/config` 中 Project instructions 来源。
2. 代理/网关场景必须画出：CLI → gateway/proxy → provider；验证 DNS 解析发生在何处，`CLAUDE_GATEWAY_PROXY_IS_EGRESS_BOUNDARY=1` 只说明 forward proxy 边界，不等于数据驻留或合规承诺。
3. skills/plugins 同步默认值要列入供应链审计：记录同步来源、禁用开关、marketplace 来源、插件 hash/manifest、rollback。
4. telemetry 需要 fail-loud：`otelHeadersHelper` 失败现在有 startup warning，POC 验收要截取该 warning/成功 exporter evidence。

**架构图组件：** `Project instruction resolver`、`Gateway sign-in confirmation`、`Forward proxy egress boundary`、`Skills/plugins sync control plane`、`Telemetry header helper`。

## 3. Codex 0.155 stable gates（voice / MCP verification / daemon recovery）

**技术问答速答：** Codex `0.155.0` 从 alpha 线进入 npm latest，release body 显示：experimental `/voice`、TUI reasoning summaries、agents overview 任务隐藏/归档/删除与 worktree ownership、local TUI Touch ID verification for MCP、daemon update schedule 与 saved threads/active goals after daemon restarts。`0.155.1` 只有标题级 release，暂不视作功能更新。

**POC gate：**
1. 用无 secret toy repo pin `@openai/codex@0.155.0`，记录 npm dist-tags、CLI version、OS/biometric capability。
2. MCP 工具要分层：普通 MCP call、需要 Touch ID 的 local TUI call、远程/CI 无 Touch ID fallback；不可把 Mac 本地生物识别当跨平台安全模型。
3. Daemon recovery 验收：启动任务→保存 active goal/thread→daemon restart→resume；输出 `EVIDENCE/daemon-recovery.md`。
4. `/voice` 仍为 experimental，客户 demo 前要验证麦克风权限、录音/转写日志保留、隐私提示。

**架构图组件：** `TUI voice channel`、`MCP local verification`、`Agent task overview`、`Managed worktree owner`、`Daemon restart recovery`。[→harness]

## 4. MAF vector-store / orchestration / tool-exposure gates（Python 1.19.0 + .NET 1.22.0）

**技术问答速答：** MAF Python 1.19.0 release-note 级新增 shared/generic vector-store provider protocols、MongoDB/Azure DocumentDB/Cosmos DB NoSQL vector-store connector、instrumentation message-event controls、per-tool `AgentModeProvider` exposure controls、built-in orchestration workflow stable names/checkpoint type registration、function calls sequential invocation option、CodeAct tool schema/description controls。`.NET 1.22.0` 看起来主要是 workflow formula state race fix、dependency/docs fixes，功能增量弱于 Python 线。

**POC gate：**
1. 向客户选型时不要只问“用哪个向量库”，而要问：filter portability、RBAC/MI 支持、PII/log redaction、latency/cost、restore/checkpoint 与 orchestration workflow name 是否稳定。
2. per-tool exposure controls 需要进入 threat model：一个工具在 chat/agent/workflow/codeact 模式中是否都可见？默认暴露面是什么？
3. sequential function call option 是安全与确定性的 trade-off：降低并发风险/审批错配，但提高时延；POC 需记录两种模式的成本和失败包络。
4. .NET 1.22.0 的 race fix 适合进入“升级前 regression checklist”，但不能说成新 capability。

**架构图组件：** `Vector provider protocol`、`Connector lane (Cosmos/DocumentDB/MongoDB/Redis/etc.)`、`Tool exposure policy`、`Workflow checkpoint registry`、`Instrumentation event filter`。

## 5. Azure MCP endpoint / remediation / mutating-tool gates（beta44/45）

**技术问答速答：** Azure MCP beta44 引入 Advisor remediation package retrieval、Storage Sync progress、ADME OSDU pagination、Azure Backup container/register/inquire/get 工作流等；beta45 继续加强 endpoint SSRF validation 的 namespace-scoped emergency overrides，并移除大量 unused/non-functional parameters。均为 changelog 级，未安装/未连 Azure。

**POC gate：**
1. 把 Azure MCP tools 分成四 lane：inventory/state-inspection、diagnostic/remediation-read、hybrid artifact generation、mutating/control-plane。Advisor remediation 的“executable artifacts”必须进入人工审批，不可自动执行。
2. Endpoint validation 不等于合规：SSRF/private-IP/public target check 只能覆盖网络目的地合法性，不能替代身份、RBAC、审计、数据驻留。
3. Backup register/inquire 属于会改变 Azure 资源状态的控制面：只允许测试订阅、最小 RBAC、pre/post state snapshot、rollback plan。
4. beta45 breaking parameter removals 要进入 tool schema freshness：agent 不能缓存旧 schema 后继续调用删除参数。

**架构图组件：** `Tool lane classifier`、`SSRF endpoint validator`、`Remediation artifact quarantine`、`Human approval + audit + rollback`。[→harness]

## 6. Skill supply-chain / eval gates（SkillSpector、SkillEvaluator、NeMo-Relay、OpenAI Agents JS）

**技术问答速答：**
- SkillSpector 2.11.x（旧源新版本/旧源新角度）强调 skill/插件包的安全扫描完整性、deadline、npm dependency/lifecycle hook/permission grants、incomplete-analysis fail-loud。
- SkillEvaluator 0.3.0 延续 validation → deduplication → live/synthetic eval 的三层质量门。
- NeMo-Relay 0.9.0（旧源复核/旧源新版本）提供 coding-agent request → isolated workers、Codex/Claude Code/Pi bundle、WebSocket lifecycle/recovery、HTTP model/hook traffic 的 relay 思路。
- OpenAI Agents JS 0.18.0 将 Docker file API 移入 running container，强调 path grants、container user、UnixLocal file protection。

**POC gate：**
1. 所有社区/第三方 skills/plugins 在安装前必须先过：license、manifest、hooks/commands/MCP、network/file-write、secret/logging、dependency/lifecycle、rollback、incomplete-analysis marker。
2. eval 不只测“能否完成任务”，还要测 skill 是否真的被用上、是否降低 token/错误率、是否引入危险工具路径。
3. Relay/daemon 架构适合画图和提问，但未经实机前不要推荐客户部署：必须验证 worker isolation、auth、session recording、hook policy、log redaction、per-user cleanup。
4. Docker/UnixLocal file APIs 的 POC 验收要包含 symlink/path traversal、new grant resume/recreate、container user permissions、large file fallback。

**架构图组件：** `Skill scanner`、`Eval tier 1/2/3`、`Relay daemon`、`Isolated worker per user/computer`、`Container file API boundary`。

## 7. Workshop exercise cards（可反哺 Agent-Harness-Engineering）

1. [→harness] **Release classifier lab**：给 Codex/Claude/MAF/Azure MCP 四个来源，要求学员标 `stable / latest / alpha / title-only / docs-only / commit-only`，并写出可/不可对客户说的话。
2. [→harness] **Instruction source lab**：toy repo 三态（`CLAUDE.md`、`AGENTS.md`、缺省）+ gateway proxy 变量，输出 instruction source report。
3. [→harness] **MCP verification lab**：模拟 local TUI MCP request，需要 Touch ID/approval/CI fallback 三种 evidence。
4. [→harness] **Azure MCP remediation quarantine lab**：把 Advisor remediation package 拆成 manual steps / hybrid / executable artifacts，必须人工审批 executable artifact。
5. [→harness] **Vector provider portability lab**：同一检索任务分别在 in-memory/Cosmos/MongoDB fixture 上跑，记录 filter/RBAC/log/latency差异。
6. [→harness] **Skill-eval gate lab**：2 个好 skill + 2 个坏 skill synthetic set，输出 validation/dedup/live-eval matrix，不安装未知 marketplace。

## 8. Fail-loud / 未完成

- 本资产未执行 CLI/SDK/smoke，不证明任何目标租户、Azure 区域、企业策略或 OS 特性可用。
- GitHub HTML/atom/raw 与 registry snapshot 会变化；客户交付前应重新 pin 版本并复核 release body。
- 任何“star 数”未在本资产中作为事实使用；如需排序/热度判断，下班要单独核 star/fork。
