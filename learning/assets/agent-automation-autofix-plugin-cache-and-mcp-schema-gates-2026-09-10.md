<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Automation / Autofix / Plugin Cache / MCP Schema-risk Precheck Gates（2026-09-10）

> 用途：给 SA 在客户技术问答、POC 部署和架构图评审中快速判断“能不能让 agent 自动跑 / 自动修 / 自动接工具 / 自动加载插件”的证据门。本文是 release/docs/commit 级预检查，尤其 Azure MCP schema 仅为 schema-risk precheck，不是已安装包或租户/本地 CLI 实机验证。
>
> 安全说明：下文出现的命令形态如 `--plugin-dir`、`azmcp ...`、`AGENTS.md`、`CLAUDE.md` 均为上游文档/变更中的工具名或配置面证据，不是让读者在生产环境直接执行。任何 smoke test 都应在临时 repo、测试订阅、无真实 secret/客户代码的隔离环境中做。

## Evidence links（可复现证据）

| 证据 | URL | 原研究快照中证据强度 | 关键命中 | Caveat |
|---|---|---|---|---|
| VS Code 1.137 release notes | https://code.visualstudio.com/updates/v1_137 | docs HTML 200 | `Automations (Preview)`, `Voice Mode`, `Agent-queued messages`, GitHub issues/PR in Agents window | 未验证企业策略、执行位置、存储边界；文档说明 queued messages 当前仅 Copilot harness 可用 |
| GitHub Code Quality agentic autofix | https://github.blog/changelog/2026-09-09-remediate-code-quality-findings-with-agentic-autofix/ | blog HTML 200 | `select up to 25 standard findings`, assign to Copilot, branch, validates, PR | 已知 07-17 覆盖过早期 agentic autofix；原研究快照中是 Code Quality 批量修复新入口/复核，不当首次发现 |
| Azure MCP Server beta.42 changelog | https://raw.githubusercontent.com/microsoft/mcp/main/servers/Azure.Mcp.Server/CHANGELOG.md | raw CHANGELOG 200 | `3.0.0-beta.42`, Advisor optimization, Data Manager for Energy, resilience drill/recoveryplan commands, `508` tool count | 未安装包/未读 schema/未连 Azure；mutating resilience tools 必须测试订阅+HITL |
| Azure MCP beta.42 release page | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.42 | release page 200 | tag reachable | release page body可能模板化；以 raw CHANGELOG 为主证据 |
| MAF client function forwarding commit | https://github.com/microsoft/agent-framework/commit/875bda6c45a26cc7240778f570d23605c4c892e5.diff | commit diff 200 | `DangerouslyAllowClientFunctionTools`, client function tools forwarding, OpenAI Responses hosting | commit-level；未确认进入正式 NuGet/未运行 sample |
| MAF file skill path revalidation commit | https://github.com/microsoft/agent-framework/commit/5b188dd80e46d6fe7ae57ca88c4a51bb2e10021b.diff | commit diff 200 | path trust boundary, revalidated immediately before use, `AgentFileSkillPathScope` | commit-level；未审完整漏洞背景/跨 OS 行为 |
| Claude Code CHANGELOG | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | raw changelog 200 | `2.1.265`, `2.1.266`, `--plugin-dir`, SubagentStart/preloaded skills prompt prefix, symlink containment, cwd persistence | npm `next=2.1.267` 有包但 raw changelog 尚无条目，标 release-source mismatch |
| Claude Code memory docs | https://code.claude.com/docs/en/memory.md | markdown 200 | `CLAUDE.md`, `@AGENTS.md`, `/context` | 文档更新是否为 09-09 实质 diff 未核 |
| Claude Code plugins docs | https://code.claude.com/docs/en/plugins.md | markdown 200 | plugins/package surface docs reachable | 具体 09-09 diff 未核；plugin 热加载主证据仍来自 raw CHANGELOG |
| Codex changelog | https://learn.chatgpt.com/docs/changelog | docs HTML 200 | Codex CLI `0.153.4`, Astra default, asynchronous questions only when tool available | `0.154.0-alpha.6.1` release body仅标题；alpha 不写客户可用功能 |
| Codex AGENTS.md docs | https://learn.chatgpt.com/docs/agent-configuration/agents-md.md | markdown 200 | discovery precedence, `AGENTS.md`, 32 KiB fallback | 未做本地 CLI smoke |
| Codex skills docs | https://learn.chatgpt.com/docs/build-skills.md | markdown 200 | progressive disclosure, `allow_implicit_invocation`, initial skills list budget | 未做触发/上下文预算实测 |
| Anthropic Claude Agent SDK Python | https://github.com/anthropics/claude-agent-sdk-python / https://pypi.org/pypi/claude-agent-sdk/json | repo/raw README/PyPI JSON 200 | PyPI latest `0.2.152` uploaded 2026-09-02; README: `allowed_tools` is auto-approve allowlist, in-process MCP custom tools, hooks, programmatic subagents | 作为 SDK intake gate 复用/浅深挖，未运行 SDK |

## 1. 技术问答速答：什么时候可以让 agent “自动跑”

**推荐话术：**

> “可以自动跑，但要先分清触发层、执行层、权限层和证据层。VS Code 1.137 已把 Automations 做成 preview，适合 hourly/daily/weekly 这类周期性 agent task；但客户环境不能只看绿色状态，必须记录触发源、workspace/repo、权限 profile、运行日志、输出 artifact 和人工确认点。”

**问答判定门：**

1. **触发源**：手动、schedule、GitHub issue/PR、Code Quality finding、外部 webhook 是否分开建模。
2. **运行位置**：本地 IDE、云端 Copilot/hosted agent、CI runner、Foundry hosted runtime 不可混写。
3. **权限 profile**：文件系统、网络、MCP server、云 RBAC、代码写入/PR 权限分别声明。
4. **证据闭环**：log、diff、test、PR、trace、evaluation score 需要可复现；“agent says done”不算完成。
5. **失败语义**：queued message、tool interruption、resume、retry、timeout、approval denied 都要有状态字段。

## 2. POC 部署清单：Agentic autofix / Code Quality 批量修复

**适用场景**：客户已有 GitHub Code Quality backlog，希望把“批量标准 finding → agent 修复 → PR review”做成治理型 POC。

**最低验收：**

| Gate | 验收问题 | 通过标准 |
|---|---|---|
| Scope | findings 是否限制在标准 Code Quality findings | 一次最多 25 条；记录 selected findings IDs 与规则类型 |
| Branch & PR | Copilot 是否独立分支修复并开 PR | PR diff 只改目标 finding 相关代码；无无关格式化风暴 |
| Validation | agent 自称 validates 是否可查 | PR 中有测试/检查日志；失败时不自动 merge |
| Enterprise policy | 是否遵循既有 GitHub Code Quality policy | policy 截图/导出作为证据；权限不绕过 required review |
| Cost | AI credits/usage 是否归因 | 每轮 finding count、token/credit 或至少运行次数入表 |
| Rollback | 批量修复失败怎么回滚 | PR close/revert 策略清楚；不直接写 protected branch |

**架构图组件**：`Code Quality Findings` → `Assign to Copilot` → `Agent branch` → `Validation Checks` → `Human PR Review` → `Merge / Close / Re-run`。

## 3. Azure MCP beta.42：成本优化 + 韧性演练变成同一张 Azure control-plane 图

beta.42 的价值不是“又多了几个工具”，而是把 **Advisor cost optimization** 与 **Resilience Management drill/recovery plan** 放进同一个 MCP 控制面：

- Advisor optimization 可回答“哪些 VM/VMSS 有节省建议、替代 SKU、当前 vs 目标利用率”。
- Resilience drill/recoveryplan 增加 add-notes / failover / resume / reprotect / finalize / retry 等更接近生产控制面的 mutating 操作。
- `advisor recommendation summary --group-by recommendation-type` 改为 GUID key，friendly display name 需用 `groups[].label`，这是 schema migration 风险。

**POC 安全红线：**

1. 只接测试订阅 / 测试 service group / 测试 vault；不接生产 DR 资源。
2. Mutating resilience tools 全部需要 human approval、操作前后 state snapshot、Azure Activity Log 对账、rollback/reprotect runbook。
3. Advisor cost optimization 首轮只读；建议不要让 agent 自动 resize，先生成 “recommendation → human decision → IaC PR” 流。
4. 大输出要检查 truncation/continuation/error envelope，避免成本建议或恢复计划被截断。

## 4. MAF commit gate：client function forwarding 与 file skill path revalidation

**Responses hosting client function forwarding（commit 875b...）**

- 关键字 `DangerouslyAllowClientFunctionTools` 说明这是 opt-in 且风险显式命名的能力。
- SA 问答重点：client-side function tool 不是 host runtime 自己执行；要画清楚“模型/host 选择工具 → client 收到 call → client 执行本地函数 → 回传结果”的边界。
- POC  gate：默认应关闭；打开前列出可转发函数清单、参数 schema、approval、日志脱敏、失败 envelope、是否允许网络/文件/云 API。

**File skill path revalidation（commit 5b188...）**

- 关键字 `path trust boundary` 与 `revalidated immediately before use` 表示发现 skill 与使用 skill 之间增加 TOCTOU 防线。
- SA 问答重点：skill/plugin 不是纯 markdown；文件路径、symlink、父目录、动态替换都属于供应链面。
- POC gate：加载前后两次校验路径；拒绝 `..`、symlink escape、大小写/分隔符混淆；记录 skill root 与 file hash。

## 5. Claude Code 2.1.265/266：plugin-dir 热加载与 prompt-cache/resume 回归

**原研究快照中可落地信号：**

- `--plugin-dir` 现在可指向“插件父目录”，运行中新增/删除 child plugin 会被拾取。
- 修复 resumed subagent / teammate 把 SubagentStart hook context、preloaded skills 或 tool list 移出 prompt prefix 导致 prompt-cache reuse 失效。
- 修复前一进程在 tool running 时死亡后的 resume：最后 prompt 不再被重写，工具调用保留并标 interrupted。
- 修复 plugin path backslash 绕过 symlink containment、双点目录名误拒、非交互 cwd 持久化等。
- `2.1.266` 是修复 `2.1.265` 的 gateway/proxy 回归；`npm next=2.1.267` 但 changelog 未公开，不能写功能结论。

**Harness 回归测试建议 [→harness]：**

1. plugin parent dir 新增/删除 child plugin 后是否热加载/卸载。
2. resumed subagent 的 tool list、system prompt prefix、preloaded skills 是否保持稳定。
3. SubagentStart hook context 是否仍在 prefix，prompt-cache hit/miss 是否可观测。
4. 进程死于 tool running 后 resume，是否保留 interrupted tool evidence。
5. plugin path：backslash、`..`、symlink、双点目录分别 fail closed。
6. non-interactive / SDK session 中 `cd` 是否跨 turn 持久。

## 6. Codex release-source freshness：stable、alpha、docs 三条线分开

原研究快照中核实：

- `@openai/codex latest=0.153.4`；官方 changelog 描述 Astra 在 bundled model picker 可见，并在未显式配置时作为 bundled default。
- `alpha=0.154.0-alpha.6.1`，但其中 `alpha-darwin-arm64=0.154.0-alpha.11-darwin-arm64` 与 generic alpha 不一致；GitHub release body 仅 “Release 0.154.0-alpha.6.1”。
- Codex docs 的 AGENTS.md / skills 页面可读，支持把 repo bootstrap 写成可测试配置面：AGENTS discovery precedence、32 KiB fallback、skills progressive disclosure、`allow_implicit_invocation`。

**规则：**

1. stable 可做客户材料基线；alpha 仅作 radar，除非 release body 或 diff 被逐文件核实。
2. 默认模型变化要在 POC 中显式记录：模型名、CLI 版本、provider、region/account、是否用户显式指定。
3. AGENTS.md / SKILL.md 的质量门要可测：加载链、shadowing、大小限制、skill trigger precision、无关 skill 是否误触发。

## 7. Anthropic Claude Agent SDK Python intake gate

PyPI latest `0.2.152`（2026-09-02）不是原快照中新包，但原研究快照中首次把它从“org 扫描”提升为 **SDK intake gate**：

- README 明确 `allowed_tools` 是 auto-approve allowlist，不是从 toolset 中移除工具；真正阻断要用 `disallowed_tools` 或 permission decision。
- `ClaudeSDKClient` 支持 bidirectional interactive conversations，且 custom tools / hooks 可作为 Python functions。
- custom tools 是 in-process MCP servers，适合 POC 中减少额外子进程，但也意味着应用进程内权限边界要更清楚。
- README 提到 settings isolation、programmatic subagents、session forking 等能力，适合后续做 SDK smoke pack。

**SA 落点：**

- 技术问答：不要把 `allowed_tools` 误讲成 denylist；它只是 auto-approve。
- POC 部署：custom tools 先用 in-process toy tool 验证 permission callback、logging、failure envelope。
- 架构图：把 SDK app 画成 `Host Python App` 内含 `ClaudeSDKClient`、`In-process MCP custom tools`、`Hooks/Permissions`，外接 `Model API` 与 `Artifacts/Logs`。

## 8. 一张架构图骨架

```text
Trigger / Source
  ├─ VS Code Automation / Voice / GitHub issue or PR
  ├─ GitHub Code Quality finding batch
  └─ Schedule / Manual / Webhook
        ↓
Agent Host / Harness
  ├─ Copilot harness / VS Code Agents window
  ├─ Codex CLI stable or alpha lane
  ├─ Claude Code latest / next / SDK app
  └─ MAF / Foundry hosted Responses host
        ↓
Policy & Packaging Plane
  ├─ AGENTS.md / CLAUDE.md bridge
  ├─ SKILL.md progressive disclosure
  ├─ Plugin parent dir / marketplace / manifest
  └─ File skill root + path revalidation
        ↓
Tool & Cloud Control Plane
  ├─ Azure MCP Advisor optimization (read-first)
  ├─ Azure MCP Resilience drill/recoveryplan (mutating, approval)
  ├─ Client function forwarding (dangerous opt-in)
  └─ In-process MCP custom tools (SDK app)
        ↓
Evidence & Review
  ├─ Branch / PR / diff
  ├─ Test / eval / trace / prompt-cache metrics
  ├─ Activity Log / audit / rollback state
  └─ Human review / independent reviewer
```

## 9. 最小 workshop 练习卡 [→harness]

1. **Release-source classifier**：给学生三条版本源（npm dist-tags、GitHub release body、docs changelog），要求输出 `stable baseline / alpha radar / mismatch`。
2. **Cross-agent repo bootstrap**：创建 `AGENTS.md` + `CLAUDE.md` 中 `@AGENTS.md` bridge，检查 Codex/Claude 加载链与大小限制。
3. **Plugin containment fixture**：用空插件目录模拟 child plugin 热加载、symlink escape、`..` path、双点目录，输出 evidence log。
4. **Azure MCP read vs mutate gate**：Advisor optimization 只读；resilience drill/recoveryplan 写操作必须 approval + audit + rollback。
5. **Agentic autofix PR gate**：用合成 finding 列表模拟最多 25 条批量修复，PR 不满足测试/人审不得 merge。

## 10. Fail-loud 列表

- 未运行 VS Code Automations、GitHub Code Quality agentic autofix、Claude Code、Codex、Claude Agent SDK 或 Azure MCP 包。
- 未验证任何企业租户策略、Azure 区域/配额/RBAC、GitHub AI credits、Copilot policy 或 Foundry preview 可用性。
- Azure MCP beta.42 的 tool schema/包内容未安装读取；只引用 raw CHANGELOG 与 release page。
- MAF 两个 commit 是 commit-level 证据，未确认进入正式 release/package。
- Claude `2.1.267 next` 与 Codex alpha dist-tag 不一致均只作 release-source mismatch，不写功能断言。
